
from aws_cdk import (
    aws_lambda,
    aws_dynamodb,
    Stack,
    Duration,
    aws_apigateway,
    aws_secretsmanager,
    aws_sqs,
    aws_lambda_event_sources as lambda_event_source,
    aws_ecr_assets,
    aws_iam,
    aws_s3, 
    aws_s3_notifications,
    CfnOutput,
    aws_events,
    aws_events_targets,
    aws_cloudwatch,
    aws_sns,
    aws_sns_subscriptions,
    aws_cloudwatch_actions,
    aws_ssm,
    RemovalPolicy
)
from constructs import Construct
import os


class S1FilingsStack(Stack):

    def __init__(self, scope: Construct, id: str, env_name: str, env_account: str, env_region: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # S3 Bucket to store PDFs - bucket creation only if not exists
        s1_pdfs_bucket = aws_s3.Bucket(self, f"S1PdfsBucket-{env_name}",
                                       bucket_name= f"data-science-s1-filings-pdfs-{env_name}",
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
                "S1_FILINGS_BUCKET": s1_pdfs_bucket.bucket_name,
          },
          function_name = f"S1RssCheckerFunction-{env_name}",
          memory_size   = 128,
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(60),
        )

        s3_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["s3:GetBucketLocation","s3:ListBucketMultipartUploads", "s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::*"]
        )
        rss_checker_lambda.add_to_role_policy(s3_policy)


        # # EventBridge rule to trigger the RSS checker daily
        # rule = aws_events.Rule(self, "S1DailyRule",
        #     # schedule=aws_events.Schedule.rate(Duration.days(1)),
        #     schedule=aws_events.Schedule.rate(Duration.minutes(2)),
        # )
        # rule.add_target(aws_events_targets.LambdaFunction(rss_checker_lambda))

       