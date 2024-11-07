import json

import pulumi
import pulumi_aws as aws
from pulumi import ResourceOptions
from pulumi_awsx import ecr as awsx_ecr

# Import configurations
config = pulumi.Config()
env_name = config.require("env")
account = aws.get_caller_identity().account_id
region = "us-west-2"
db_cluster_arn = config.require("db_cluster_arn")
database_name = config.require("database_name")
secret_arn = config.require("secret_arn")
s1_bucket_name = config.require("file_assets_bucket_name")
team = config.require("team")

# Define IAM Role ARNs
# role_arn = f"arn:aws:iam::{account}:role/data-science-s1-filings-cdk"

role_name = f"data-science-s1-filings-role-{env_name}"

# Create IAM Role with Assume Role Policy for Lambda Service
s1_filings_role = aws.iam.Role(role_name,
                               name=role_name,
                               assume_role_policy=json.dumps({
                                   "Version": "2012-10-17",
                                   "Statement": [
                                       {
                                           "Effect": "Allow",
                                           "Principal": {"Service": "lambda.amazonaws.com"},
                                           "Action": "sts:AssumeRole"
                                       }
                                   ]
                               }),
                               )

# Define policy document for required permissions
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetBucketLocation",
                "s3:ListBucketMultipartUploads",
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sqs:SendMessage",
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl",
                "sqs:ChangeMessageVisibility"
            ],
            "Resource": f"arn:aws:sqs:{region}:{account}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "kms:Decrypt",
                "kms:Encrypt",
                "kms:ReEncrypt*",
                "kms:GenerateDataKey*",
            ],
            "Resource": f"arn:aws:kms:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "rds-data:ExecuteStatement",
                "rds-data:BatchExecuteStatement"
            ],
            "Resource": f"arn:aws:rds:{region}:{account}:cluster:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": f"arn:aws:secretsmanager:{region}:{account}:secret:*"
        }
    ]
}

# Create an inline policy for the role
policy = aws.iam.RolePolicy(f"data-science-s1-filings-policy-{env_name}",
                            role=s1_filings_role.name,
                            policy=json.dumps(policy_document)
                            )

# Export the role ARN for reference in other resources
pulumi.export("roleArn", s1_filings_role.arn)

# S3 Bucket for HTML storage
s1_filings_bucket = aws.s3.Bucket(f"s1-filings-bucket-{env_name}",
                                  bucket=s1_bucket_name,
                                  versioning={"enabled": True},
                                  # opts=ResourceOptions(protect=True)
                                  )

# SQS Dead-Letter Queue (DLQ)
s1_dlq = aws.sqs.Queue(
    f"s1-filings-dlq-{env_name}",
    visibility_timeout_seconds=300,
    message_retention_seconds=1209600,  # 14 days
)

# SQS Queue with DLQ attached
s1_queue = aws.sqs.Queue(
    f"s1-filings-queue-{env_name}",
    visibility_timeout_seconds=960,
    redrive_policy=s1_dlq.arn.apply(lambda arn: json.dumps({
        "deadLetterTargetArn": arn,  # Ensure arn is treated as a single string
        "maxReceiveCount": 5,
    })),
)

# Create IAM Policies for Lambda permissions
s3_policy = aws.iam.Policy(f"data-science-s3-policy-{env_name}",
                           policy=pulumi.Output.all(s1_filings_bucket.arn).apply(lambda arn: f"""{{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Effect": "Allow",
                "Action": ["s3:*"],
                "Resource": ["{arn}"]
            }}
        ]
    }}""")
                           )

repository = aws.ecr.Repository(f"data-science-s1-filings-{env_name}", name=f"data-science-s1-filings-{env_name}")

ecr_image = awsx_ecr.Image(f"s1-filings-image-{env_name}",
                           repository_url=repository.repository_url,
                           image_tag="latest",  # TODO: tag images with version
                           context="../../../../",  # The directory with the Dockerfile
                           dockerfile="../../../../deployments/Dockerfile.s1_filings",
                           platform="linux/amd64"
                           )

# Lambda function for RSS Checker
rss_checker_lambda = aws.lambda_.Function(f"s1-rss-checker-lambda-{env_name}",
                                          package_type="Image",
                                          image_uri=ecr_image.image_uri,
                                          memory_size=1024,
                                          timeout=900,
                                          environment={
                                              "variables": {
                                                  "S1_FILINGS_BUCKET": s1_filings_bucket.bucket,
                                                  "S1_QUEUE_URL": s1_queue.url,
                                              }
                                          },
                                          image_config=aws.lambda_.FunctionImageConfigArgs(
                                              commands=["s1-filings.lambda.rss_checker.main.handler"]
                                          ),
                                          role=s1_filings_role.arn,
                                          )

# Lambda function for S1 Extractor
s1_extractor_lambda = aws.lambda_.Function(f"s1-extractor-lambda-{env_name}",
                                           package_type="Image",
                                           image_uri=ecr_image.image_uri,
                                           memory_size=1024,
                                           timeout=900,
                                           environment={
                                               "variables": {
                                                   "S1_FILINGS_BUCKET": s1_filings_bucket.bucket,
                                                   "DB_CLUSTER_ARN": db_cluster_arn,
                                                   "DATABASE_NAME": database_name,
                                                   "SECRET_ARN": secret_arn,
                                               }
                                           },
                                           image_config=aws.lambda_.FunctionImageConfigArgs(
                                               commands=["s1-filings.lambda.s1_extractor.main.handler"]
                                           ),
                                           role=s1_filings_role.arn,
                                           )

# Add SQS Event Source to the S1 Extractor Lambda
s1_extractor_event_source = aws.lambda_.EventSourceMapping(
    resource_name=f"s1-extractor-event-source-{env_name}",
    event_source_arn=s1_queue.arn,
    function_name=s1_extractor_lambda.name,
    batch_size=10,  # Number of records to process in one batch
    enabled=True  # Enable the event source mapping immediately
)

# IAM Policy Attachments for Lambda Permissions
aws.iam.RolePolicyAttachment(f"rss-checker-s3-access-policy-attachment-{env_name}",
                             role=s1_filings_role.name,
                             policy_arn=s3_policy.arn)

aws.iam.RolePolicyAttachment(f"s1-extractor-s3-access-policy-attachment-{env_name}",
                             role=s1_filings_role.name,
                             policy_arn=s3_policy.arn)

# Grant RDS and Secrets Manager permissions to the S1 Extractor Lambda
rds_policy = aws.iam.Policy(f"rds-policy-attachment-{env_name}",
                            policy=pulumi.Output.all(db_cluster_arn).apply(lambda arn: f"""{{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Effect": "Allow",
                "Action": ["rds-data:ExecuteStatement", "rds-data:BatchExecuteStatement"],
                "Resource": "{arn}"
            }}
        ]
    }}""")
                            )
secrets_policy = aws.iam.Policy(f"secrets-policy-attachment-{env_name}",
                                policy=pulumi.Output.all(secret_arn).apply(lambda arn: f"""{{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                "Resource": "{arn}"
            }}
        ]
    }}""")
                                )

aws.iam.RolePolicyAttachment(f"s1-extractor-rds-access-policy-attachment-{env_name}",
                             role=s1_filings_role.name,
                             policy_arn=rds_policy.arn)

aws.iam.RolePolicyAttachment(f"s1-extractor-secrets-access-policy-attachment-{env_name}",
                             role=s1_filings_role.name,
                             policy_arn=secrets_policy.arn)

# Grant SQS permissions
aws.sqs.QueuePolicy(f"sqs-policy-attachment-{env_name}",
                    queue_url=s1_queue.url,
                    policy=pulumi.Output.all(s1_queue.arn, s1_dlq.arn).apply(lambda arns: json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "lambda.amazonaws.com"},
                                "Action": "sqs:SendMessage",
                                "Resource": f"{arns[0]}"
                            },
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "lambda.amazonaws.com"},
                                "Action": "sqs:ReceiveMessage",
                                "Resource": f"{arns[1]}"
                            }
                        ]
                    }))
                    )

# Export Outputs
pulumi.export("s1_bucket_name", s1_filings_bucket.bucket)
pulumi.export("s1_queue_url", s1_queue.url)
