
from aws_cdk import (
    aws_lambda,
    aws_sqs,
    aws_ecr_assets,
    aws_stepfunctions,
    aws_stepfunctions_tasks,
    aws_batch as batch,
    aws_s3 as s3,
    aws_ec2 as ec2,
    Stack,
    Duration,
    aws_iam,
    aws_lambda_event_sources as lambda_event_source,
    aws_s3_notifications as s3n
)

from constructs import Construct
import os

class NewsEvaluationStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # SQS queue
        evaluation_queue = aws_sqs.Queue(
            self, "EvaluationQueue",
            visibility_timeout=Duration.seconds(300)
        )

        bucket_name = "data-science-news-output"
        news_bucket = s3.Bucket.from_bucket_name(self, "ImportedNewsBucket", bucket_name=bucket_name)

        # Lambda function that fetches initial data
        news_evaluation_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/news_evaluation/news_evaluation_data_fetcher"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )
        news_evaluation_lambda = aws_lambda.Function(self, 
            id            = "NewsEvaluationDataFetcherLambdaFunction",
            description   = "NewsEvaluationDataFetcherLambdaFunction",
            code          = news_evaluation_ecr_image,
            handler       = aws_lambda.Handler.FROM_IMAGE,
            runtime       = aws_lambda.Runtime.FROM_IMAGE,
            environment={
                'EVALUATION_QUEUE_URL': evaluation_queue.queue_url,
                'S3_BUCKET': bucket_name
            },
            function_name = "NewsEvaluationDataFetcherFunction",
            memory_size   = 128,
            reserved_concurrent_executions = 10,
            timeout       = Duration.seconds(60),
        )

        # Add the S3 trigger
        notification = s3n.LambdaDestination(news_evaluation_lambda)
        news_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, notification)

        s3_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["s3:GetBucketLocation","s3:ListBucketMultipartUploads", "s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::*"]
        )
        news_evaluation_lambda.add_to_role_policy(s3_policy)


        # Grant the Lambda function permission to send messages to the SQS queue
        evaluation_queue.grant_send_messages(news_evaluation_lambda)


        # A service role for AWS Batch
        batch_service_role = aws_iam.Role(
            self, "BatchServiceRole",
            assumed_by=aws_iam.ServicePrincipal("batch.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSBatchServiceRole")
            ]
        )

        # An instance role for EC2 instances in the compute environment
        instance_role = aws_iam.Role(
            self, "BatchInstanceRole",
            assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"),
                
            ]
        )

        # An instance profile for the instance role
        instance_profile = aws_iam.CfnInstanceProfile(
            self, "BatchInstanceProfile",
            roles=[instance_role.role_name]
        )

        vpc = ec2.Vpc.from_lookup(self, "Vpc", is_default=True)  # Using the default VPC

        security_group = ec2.SecurityGroup(
            self, "BatchSecurityGroup",
            vpc=vpc,
            description="Security group for Batch compute environment",
            allow_all_outbound=True  # ToDo: Might need to modify this?
        )

        
        # AWS Batch Compute Environment
        compute_env = batch.CfnComputeEnvironment(
            self, "NewsEvaluationBatchComputeEnv",
            type="MANAGED", 
            compute_environment_name="NewsEvaluationBatchComputeEnv", 
            service_role=batch_service_role.role_arn, 
            compute_resources=batch.CfnComputeEnvironment.ComputeResourcesProperty(
                type="EC2",  
                subnets=["subnet-2d775f54", "subnet-b5995c9e"],  # these are default VPCs, we may need to create a new vpc.
                security_group_ids=[security_group.security_group_id],
                minv_cpus=0,
                desiredv_cpus=4,  
                instance_types=["m5.large", "m5.xlarge"],  
                maxv_cpus=16,
                instance_role=instance_profile.attr_arn
            )
        )


        # AWS Batch Job Queue
        job_queue = batch.CfnJobQueue(
            self, "NewsEvaluationJobQueue",
            job_queue_name="NewsEvaluationJobQueue",
            compute_environment_order=[
                {
                    "computeEnvironment": compute_env.ref,
                    "order": 1
                }
            ],
            priority=1
        )



        # AWS Batch Job Definitions
        job_definition_ecr_image_1 = aws_ecr_assets.DockerImageAsset(
            self, "BatchJobImage1",
            directory = os.path.join(os.getcwd(), "news_evaluation/batch_jobs/job_1")
        )
        batch_job_role = aws_iam.Role(
            self, "BatchJobRole",
            assumed_by=aws_iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            inline_policies={
                "S3WritePolicy": aws_iam.PolicyDocument(statements=[
                    aws_iam.PolicyStatement(
                        actions=["s3:PutObject"],
                        resources=[f"arn:aws:s3:::{bucket_name}/*"]
                    )
                ])
            }
        )


        job_definition_1 = batch.CfnJobDefinition(
            self, "NewsEvaluationBatchJobDefinition1",
            job_definition_name="NewsEvaluationBatchJobDefinition1",
            container_properties={
                "image": job_definition_ecr_image_1.image_uri,
                "memory": 1024,
                "vcpus": 1,
                "jobRoleArn": batch_job_role.role_arn,
                "environment": [
                    {
                        "name": "BUCKET_NAME",
                        "value": bucket_name
                    },
                    {
                        "name": "INPUT_DATA",
                        "value.$": "$.newsData"  # Use the input data from the state machine - news_evaluation_stfn_trigger                    
                    }
                ]
            },
            type="container"
        )

        job_definition_ecr_image_2 = aws_ecr_assets.DockerImageAsset(
            self, "BatchJobImage2",
            directory = os.path.join(os.getcwd(), "news_evaluation/batch_jobs/job_2")
        )

        job_definition_2 = batch.CfnJobDefinition(
            self, "NewsEvaluationBatchJobDefinition2",
            job_definition_name="NewsEvaluationBatchJobDefinition2",
            container_properties={
                "image": job_definition_ecr_image_2.image_uri,
                "memory": 1024,
                "vcpus": 1,
                "jobRoleArn": batch_job_role.role_arn
            },
            type="container"
        )

        # Step Functions tasks for triggering Batch jobs
        trigger_batch_task_1 = aws_stepfunctions_tasks.BatchSubmitJob(
            self, "NewsEvaluationTriggerBatchTask1",
            job_definition_arn=job_definition_1.ref,  
            job_name="NewsEvaluationProcessDataJob1",
            job_queue_arn=job_queue.ref,
        )


        trigger_batch_task_2 = aws_stepfunctions_tasks.BatchSubmitJob(
            self, "NewsEvaluationTriggerBatchTask2",
            job_definition_arn=job_definition_2.ref,  
            job_name="NewsEvaluationProcessDataJob2",
            job_queue_arn=job_queue.ref,
        )

        # Seuential batch jobs
        definition = trigger_batch_task_1.next(trigger_batch_task_2)

        state_machine = aws_stepfunctions.StateMachine(
            self, "NewsEvaluationBatchJobsSM",
            state_machine_name="NewsEvaluationBatchJobsSM",
            definition_body=aws_stepfunctions.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(30)
        )

        ## Parallel batch jobs
        # parallel_state = sfn.Parallel(self, "ParallelBatchJobs")
        # parallel_state.branch(trigger_batch_task_1)
        # parallel_state.branch(trigger_batch_task_2)

        # state_machine = aws_stepfunctions.StateMachine(
        #     self, "BatchJobsStateMachine",
        #     definition_body=aws_stepfunctions.DefinitionBody.from_chainable(parallel_state),
        #     timeout=Duration.minutes(30)
        # )

        state_machine_arn = state_machine.state_machine_arn

        stfn_trigger_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/news_evaluation/news_evaluation_stfn_trigger"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        stfn_trigger_lambda = aws_lambda.Function(self,
          id            = "NewsEvaluationSFTriggerLambdaFunction",
          description   = "NewsEvaluationSFTriggerLambdaFunction",
          code          = stfn_trigger_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          environment   = {
                "STATE_MACHINE_ARN": state_machine_arn
          },
          function_name = "NewsEvaluationSFTriggerFunction",
          memory_size   = 128,
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(60),
        )

        
        # Grant the Lambda function permissions to read from the queue
        evaluation_queue.grant_consume_messages(stfn_trigger_lambda)
        
        # Create an SQS event source for Lambda
        issuers_event_source = lambda_event_source.SqsEventSource(evaluation_queue)

        # Add SQS event source to the Lambda function
        stfn_trigger_lambda.add_event_source(issuers_event_source)

        # Permission to start executions of the state machine
        step_functions_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["states:StartExecution"],
            resources=[state_machine_arn]
        )
        stfn_trigger_lambda.add_to_role_policy(step_functions_policy)
