from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_ssm as ssm,
    Duration,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_scheduler as scheduler,
    aws_scheduler_targets as scheduler_targets,
    TimeZone,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_logs as logs,
)
from constructs import Construct

class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        user_profile_table=dynamodb.TableV2(
            self, "UserProfileTable",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(point_in_time_recovery_enabled=True),
            removal_policy=RemovalPolicy.RETAIN
        )
        tasks_table=dynamodb.TableV2(
                    self, "TasksTable",
                    partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name="task_id", type=dynamodb.AttributeType.STRING),
                    point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(point_in_time_recovery_enabled=True),
                    removal_policy=RemovalPolicy.RETAIN
                )
        plans_table=dynamodb.TableV2(
                    self, "PlansTable",
                    partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
                    sort_key=dynamodb.Attribute(name="plan_date", type=dynamodb.AttributeType.STRING),
                    time_to_live_attribute="expires_at",
                    removal_policy=RemovalPolicy.DESTROY
                )
        icalendar_layer = _lambda.LayerVersion(
            self, "IcalendarLayer",
            code=_lambda.Code.from_asset("layers/icalendar"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12]
        )

        sync_logs = logs.LogGroup(self, "SyncLogs", retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY)
        planner_logs = logs.LogGroup(self, "PlannerLogs", retention=logs.RetentionDays.ONE_MONTH, removal_policy=RemovalPolicy.DESTROY)
        
        calendar_sync_fn = _lambda.Function(
            self, "CalendarSyncFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="sync.lambda_handler",
            code=_lambda.Code.from_asset("lambdas/calendar_sync"),
            layers=[icalendar_layer],
            timeout=Duration.seconds(60),
            environment={"TABLE_NAME": tasks_table.table_name},
            log_group=sync_logs,
        )

        planner_fn = _lambda.Function(
            self, "PlannerFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="planner.lambda_handler",
            code=_lambda.Code.from_asset("lambdas/planner"),
            timeout=Duration.seconds(60),
            environment={"TABLE_NAME": tasks_table.table_name, "PLANS_TABLE": plans_table.table_name},
            layers=[icalendar_layer],
            log_group=planner_logs,
        )

        tasks_table.grant_read_data(planner_fn)
        plans_table.grant_read_write_data(planner_fn)

        feed_url_param = ssm.StringParameter.from_secure_string_parameter_attributes(
            self, "FeedUrlParam",
            parameter_name="/playbook/schoology-feed-url"
        )

        tasks_table.grant_read_write_data(calendar_sync_fn)
        feed_url_param.grant_read(calendar_sync_fn)

        planner_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
                ],
        ))

        sync_step = tasks.LambdaInvoke(self, "SyncStep", lambda_function=calendar_sync_fn)
        planner_step = tasks.LambdaInvoke(self, "PlannerStep", lambda_function=planner_fn)

        sync_step.add_retry(
            errors=["States.ALL"],
            max_attempts=2,
            interval=Duration.seconds(30),
            backoff_rate=2
        )

        planner_step.add_retry(
                    errors=["States.ALL"],
                    max_attempts=2,
                    interval=Duration.seconds(30),
                    backoff_rate=2
                )

        sync_step.add_catch(planner_step, result_path="$.sync_error")

        definition = sync_step.next(planner_step)
        nightly_workflow = sfn.StateMachine(
            self, "NightlyWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(10)
        )

        scheduler.Schedule(
            self, "NightlySchedule",
            schedule=scheduler.ScheduleExpression.cron(
                minute="0", hour="2", time_zone=TimeZone.AMERICA_NEW_YORK
            ),
            target=scheduler_targets.StepFunctionsStartExecution(nightly_workflow),
            description="Nightly calendar sync + plan at 2am Eastern",
        )

        alert_email = self.node.try_get_context("alert_email")
        alerts_topic = sns.Topic(self, "AlertsTopic")
        if alert_email:
            alerts_topic.add_subscription(subs.EmailSubscription(alert_email))

        workflow_alarm = cloudwatch.Alarm(
            self, "WorkflowFailedAlarm",
            metric=nightly_workflow.metric_failed(period=Duration.hours(1)),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        workflow_alarm.add_alarm_action(cw_actions.SnsAction(alerts_topic))

        sync_alarm = cloudwatch.Alarm(
            self, "SyncErrorsAlarm",
            metric=calendar_sync_fn.metric_errors(period=Duration.hours(1)),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        sync_alarm.add_alarm_action(cw_actions.SnsAction(alerts_topic))