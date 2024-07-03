import os

from aws_cdk import Duration, RemovalPolicy, Stack  # aws_sqs as sqs,
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3_notifications

# from aws_cdk.aws_lambda_python import PythonFunction
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct


class SectorClassificationTrainStack(Stack):

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
            f"sector-classification-aiml-train-{env_name}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Define the IAM role for SageMaker
        target_role = iam.Role(
            self,
            "sector-class-model-train-sagemaker-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            description="Role assumed by Lambda to perform Hugging Face training job",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess"
                ),
            ],
        )

        # Define Lambda function
        lambda_function = PythonFunction(
            self,
            "StartTrainingLambda",
            entry="lambda",  # Directory containing lambda function code
            runtime=lambda_.Runtime.PYTHON_3_10,
            index="start_training.py",
            handler="handler",  # Assumes your handler is defined in start_training.py as 'handler'
            # role=lambda_role,
            timeout=Duration.seconds(300),  # Adjust timeout as needed
            architecture=lambda_.Architecture.ARM_64,
            memory_size=1024,
            environment={"TARGET_ROLE_ARN": target_role.role_arn},
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
                    "sagemaker:ListTags",
                    "sagemaker:CreateTrainingJob",
                    "sagemaker:DescribeTrainingJob",
                    "sagemaker:CreateExperiment",
                    "sagemaker:DescribeExperiment",
                    "sagemaker:CreateTrial",
                    "sagemaker:DescribeTrial",
                    "sagemaker:CreateTrialComponent",
                    "sagemaker:DescribeTrialComponent",
                    "sagemaker:AddTags",
                    "sagemaker:Search",
                    "sagemaker:AssociateTrialComponent",
                    "sagemaker:UpdateTrialComponent",
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
            s3.NotificationKeyFilter(prefix="inputs/", suffix=".json"),
        )
