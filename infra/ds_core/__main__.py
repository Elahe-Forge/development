import pulumi
import pulumi_aws as aws

config = pulumi.Config()

stack = config.require("environment")

# Create an AWS resource (S3 Bucket)
db_secret = aws.secretsmanager.Secret(
    resource_name=f"{stack}-ds-secrets",
    name=f"{stack}-ds-secrets",
    description="Managed secrets for the data science team.",
)
