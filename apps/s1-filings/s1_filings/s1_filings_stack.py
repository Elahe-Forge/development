
from aws_cdk import (
    aws_lambda,
    Stack,
    Duration,
    aws_sqs,
    aws_lambda_event_sources as lambda_event_source,
    aws_ecr_assets,
    aws_iam,
    aws_s3, 
    RemovalPolicy
)
from constructs import Construct
import os


class S1FilingsStack(Stack):

    def __init__(self, scope: Construct, id: str, env_name: str, env_account: str, env_region: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        
        # DLQ for s1_queue
        s1_dlq = aws_sqs.Queue(
            self, "S1FilingsDLQ",
            queue_name=f"S1FilingsDLQ-{env_name}",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14)  # Messages are retained for 14 days
        )


        s1_queue = aws_sqs.Queue(
            self, 'S1FilingsQueue',
            visibility_timeout=Duration.seconds(960), # 16 mins - slightly higher than lambda timeout
            queue_name=f"S1FilingsQueue-{env_name}",
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                max_receive_count=5,  # Number of receive attempts before moving to DLQ
                queue=s1_dlq
            )
        )

        # S3 Bucket to store HTML files - bucket creation only if not exists
        s1_html_bucket = aws_s3.Bucket(self, f"S1HtmlsBucket-{env_name}",
                                       bucket_name= f"data-science-s1-filings-htmls-{env_name}",
                                       versioned=True,
                                       removal_policy=RemovalPolicy.RETAIN)  # Retain bucket on stack deletion

        rss_checker_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/rss_checker"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        rss_checker_lambda = aws_lambda.Function(self,
          id            = "S1RssCheckerLambdaFunction",
          description   = "S1RssCheckerLambdaFunction",
          code          = rss_checker_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          environment   = {
                "S1_FILINGS_HTML_BUCKET": s1_html_bucket.bucket_name,
                "S1_QUEUE_URL": s1_queue.queue_url,
          },
          function_name = f"S1RssCheckerFunction-{env_name}",
          memory_size   = 1024, 
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(900),
        )

        s3_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["s3:GetBucketLocation","s3:ListBucketMultipartUploads", "s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::*"]
        )
        rss_checker_lambda.add_to_role_policy(s3_policy)

        s1_queue.grant_send_messages(rss_checker_lambda)

        # S3 Bucket to store S1 results - bucket creation only if not exists
        s1_output_bucket = aws_s3.Bucket(self, f"S1OutputBucket-{env_name}",
                                       bucket_name= f"data-science-s1-filings-output-{env_name}",
                                       versioned=True,
                                       removal_policy=RemovalPolicy.RETAIN)  # Retain bucket on stack deletion

        
        snowflake_credentials_nonprod = {
            "account":"FORGEGLOBAL_NONPROD",
            "private_key_passphrase":None,
            "warehouse":"COMPUTE_WH",
            "database":"source",
            "db_schema":"s1_fillings",
            "table_name":"data_ops_fields_extraction"
        }
        snowflake_credentials = snowflake_credentials_nonprod if env_name == 'dev' else None
        secret_arn = f"arn:aws:secretsmanager:{env_region}:{env_account}:secret:nonprod-ds-secrets-5MfieR" if env_name == 'dev' else ""

        s1_extractor_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/s1_extractor"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        s1_extractor_lambda = aws_lambda.Function(self,
          id            = "S1ExtractorLambdaFunction",
          description   = "S1ExtractorLambdaFunction",
          code          = s1_extractor_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          environment   = {
                'S1_FILINGS_HTML_BUCKET': s1_html_bucket.bucket_name,
                'S3_S1_OUTPUT_BUCKET': s1_output_bucket.bucket_name,
                'SNOWFLAKE_CREDENTIALS': snowflake_credentials,
                'SECRET_ARN': secret_arn,
                'REGION_NAME': env_region
          },
          function_name = f"S1ExtractorFunction-{env_name}",
          memory_size   = 1024, 
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(900),
        )

        s1_extractor_lambda.add_to_role_policy(s3_policy)

        
        # Grant the Lambda function permissions to read from the queue
        s1_queue.grant_consume_messages(s1_extractor_lambda)

        # Add SQS event source to the Lambda function
        s1_queue_event_source = lambda_event_source.SqsEventSource(s1_queue) 
        s1_extractor_lambda.add_event_source(s1_queue_event_source)

        # Add permissions to the Lambda function to access the secret manager for snowflake credentials
        secrets_policy_statement = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=[ "secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
            resources=[secret_arn]
        )
        s1_extractor_lambda.add_to_role_policy(secrets_policy_statement)

        # # EventBridge rule to trigger the RSS checker daily
        # rule = aws_events.Rule(self, "S1DailyRule",
        #     # schedule=aws_events.Schedule.rate(Duration.days(1)),
        #     schedule=aws_events.Schedule.rate(Duration.minutes(2)),
        # )
        # rule.add_target(aws_events_targets.LambdaFunction(rss_checker_lambda))

       