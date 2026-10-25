from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_ssm as ssm,
    Duration,
    aws_iam as iam
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

        calendar_sync_fn = _lambda.Function(
            self, "CalendarSyncFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="sync.lambda_handler",
            code=_lambda.Code.from_asset("lambdas/calendar_sync"),
            layers=[icalendar_layer],
            timeout=Duration.seconds(60),
            environment={"TABLE_NAME": tasks_table.table_name}
        )

        planner_fn = _lambda.Function(
            self, "PlannerFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="planner.lambda_handler",
            code=_lambda.Code.from_asset("lambdas/planner"),
            timeout=Duration.seconds(60),
            environment={"TABLE_NAME": tasks_table.table_name, "PLANS_TABLE": plans_table.table_name},
            layers=[icalendar_layer]
        )

        tasks_table.grant_read_data(planner_fn)
        plans_table.grant_write_data(planner_fn)

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