from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    RemovalPolicy
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

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "InfraQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )
