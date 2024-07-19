import os

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3_notifications
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from constructs import Construct
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
email_subscriber = os.getenv("EMAIL_SUBSCRIBER")


class SectorClassBatchInferStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        env_account: str,
        env_region: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create an S3 bucket
        bucket = s3.Bucket(
            self,
            "sector-class-batch-infer-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            bucket_name=f"{env_name}-sector-class-batch-infer",
        )

        # Create SNS Topic for Lambda Error
        topic = sns.Topic(
            self,
            "SectorClassBatchTransformTopic",
            display_name="Sector Class Batch Transform Lambda Error Notifications",
        )

        # Define the IAM role for SageMaker
        target_role = iam.Role(
            self,
            "sector-class-batch-infer-sagemaker-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            description="Role assumed by Lambda to perform Batch Inference for Sector Classification",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
            ],
        )

        # Define the Lambda function resource
        lambda_function = lambda_.DockerImageFunction(
            self,
            "SectorClassBatchInferFunc",
            code=lambda_.DockerImageCode.from_image_asset(
                "./image"
            ),  # Points to the lambda directory
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(30),
            environment={
                "TARGET_ROLE_ARN": target_role.role_arn,
                "TOPIC_ARN": topic.topic_arn,
            },
        )

        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:GetBucketLocation",
                ],
                resources=["arn:aws:s3:::*", "arn:aws:s3:::*/*"],
            )
        )

        # Add policy to allow SageMaker CreateModel
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateModel",
                    "sagemaker:CreateTransformJob",
                    "sagemaker:DescribeTransformJob",
                    "sagemaker:StopTransformJob",
                    "sagemaker:ListTags",
                    "sagemaker:ListTransformJobs",
                ],
                resources=["*"],  # Adjust this to the specific resources if needed
            )
        )

        # Add policy to allow passing the SageMaker execution role
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[target_role.role_arn],
            )
        )

        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=["arn:aws:logs:*:*:*"],
            )
        )

        # Grant the Lambda function read permissions on the S3 bucket
        bucket.grant_read(lambda_function)

        # Add an S3 bucket notification to trigger the Lambda function for the "inputs/" folder
        notification = s3_notifications.LambdaDestination(lambda_function)
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            notification,
            s3.NotificationKeyFilter(prefix="inputs/data_input/", suffix=".csv"),
        )

        # Grant Lambda permissions to publish to the SNS topic
        topic.grant_publish(lambda_function)

        # Add an email subscription to the SNS topic (optional)
        topic.add_subscription(subs.EmailSubscription(email_subscriber))

        # Create an SNS topic
        transform_job_topic = sns.Topic(
            self,
            "TransformJobTopic",
            display_name="SageMaker Sector Classification Batch Transform Job Notifications",
        )

        # Add an email subscription to the SNS topic
        transform_job_topic.add_subscription(subs.EmailSubscription(email_subscriber))

        # Create an EventBridge rule for SageMaker transform job state change
        rule = events.Rule(
            self,
            "SageMakerTransformJobRule",
            event_pattern={
                "source": ["aws.sagemaker"],
                "detail_type": ["SageMaker Transform Job State Change"],
                "detail": {
                    "TransformJobStatus": ["Completed", "Failed"],
                    "TransformJobName": [{"prefix": "sector-classification"}],
                },
            },
        )

        # Add SNS topic as the target of the EventBridge rule
        rule.add_target(targets.SnsTopic(transform_job_topic))
