
from aws_cdk import (
    aws_lambda,
    aws_sqs,
    aws_ecr_assets,
    Stack,
    Duration,
    aws_iam,
    aws_lambda_event_sources as lambda_event_source,
    aws_s3_notifications as s3n,
    aws_apigateway,
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

        # Lambda function that fetches initial data
        news_evaluation_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/news_evaluation/news_evaluation_data_fetcher"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )
        news_evaluation_lambda = aws_lambda.Function(self, 
            id            = "NewsEvaluationNewsEvaluationDataFetcherLambdaFunction",
            description   = "NewsEvaluationNewsEvaluationDataFetcherLambdaFunction",
            code          = news_evaluation_ecr_image,
            handler       = aws_lambda.Handler.FROM_IMAGE,
            runtime       = aws_lambda.Runtime.FROM_IMAGE,
            environment={
                'EVALUATION_QUEUE_URL': evaluation_queue.queue_url,
                'S3_BUCKET': bucket_name
            },
            function_name = "NewsEvaluationDataFetcherFunction",
            memory_size   = 1024,
            reserved_concurrent_executions = 10,
            timeout       = Duration.seconds(300),
        )

        # # Add the S3 trigger
        # notification = s3n.LambdaDestination(news_evaluation_lambda)
        # news_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, notification)

        s3_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["s3:GetBucketLocation","s3:ListBucketMultipartUploads", "s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::*"]
        )
        news_evaluation_lambda.add_to_role_policy(s3_policy)


        # Grant the Lambda function permission to send messages to the SQS queue
        evaluation_queue.grant_send_messages(news_evaluation_lambda)

        # API Gateway to trigger the Lambda function 
        api_eval = aws_apigateway.LambdaRestApi(
            self, 'NewsEvaluationApi',
            handler=news_evaluation_lambda,
            proxy=False,
            rest_api_name='NewsEvaluationApi'
        )

        # Resource for running all companies
        run_all_resource = api_eval.root.add_resource('run-all')
        run_all_resource.add_method('POST')

        # Resource for running a specific issuer
        run_issuer_resource = api_eval.root.add_resource('run-issuer')
        run_issuer_resource.add_method('POST')


        # Define the IAM role for Lambda
        lambda_role = aws_iam.Role(self, "LambdaExecutionRole",
                                   assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
                                   managed_policies=[
                                       aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                                       aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
                                   ])

        # Custom policy to allow invoking Bedrock model
        lambda_role.add_to_policy(aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=["arn:aws:bedrock:us-west-2::foundation-model/*"]
        ))

        llm_trigger_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/news_evaluation/news_evaluation_llm_trigger"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        llm_trigger_lambda = aws_lambda.Function(self,
          id            = "NewsEvaluationLLMTriggerLambdaFunction",
          description   = "NewsEvaluationLLMTriggerLambdaFunction",
          code          = llm_trigger_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          role=lambda_role,
          environment   = {
                'S3_BUCKET': bucket_name
          },
          function_name = "NewsEvaluationLLMTriggerFunction",
          memory_size   = 1024, # default 128 causes memory allocation limit error
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(300)
        )

        
        # Grant the Lambda function permissions to read from the queue
        evaluation_queue.grant_consume_messages(llm_trigger_lambda)
        
        # Create an SQS event source for Lambda
        issuers_event_source = lambda_event_source.SqsEventSource(evaluation_queue)

        # Add SQS event source to the Lambda function
        llm_trigger_lambda.add_event_source(issuers_event_source)

        s3_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["s3:GetBucketLocation","s3:ListBucketMultipartUploads", "s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::*"]
        )
        llm_trigger_lambda.add_to_role_policy(s3_policy)






