#!/usr/bin/env python3
import os

from aws_cdk import App, DefaultStackSynthesizer, Environment, Tags

from coi_reader.coi_reader_stack import CoiReaderStack

app = App()

env_name = app.node.try_get_context("env")
env_context = app.node.try_get_context(env_name)

account = env_context["account"]
region = env_context["region"]
bucket_name = env_context["file_assets_bucket_name"]
team = env_context["team"]

env = Environment(account=account, region=region)

role_arn = f"arn:aws:iam::{account}:role/data-science-sector-class-cdk-{env_name}"

synthesizer = DefaultStackSynthesizer(
    deploy_role_arn=role_arn,
    cloud_formation_execution_role=role_arn,
    file_asset_publishing_role_arn=role_arn,
    image_asset_publishing_role_arn=role_arn,
    file_assets_bucket_name=bucket_name,
)


my_stack = CoiReaderStack(
    app,
    f"coi-reader-{env_name}",
    env_name=env_name,
    env_account=account,
    env_region=region,
    env=env,
    synthesizer=synthesizer,
)

Tags.of(my_stack).add("team", team)

app.synth()


# app = App()
# CoiReaderStack(app, "CoiReaderStack",
#     # If you don't specify 'env', this stack will be environment-agnostic.
#     # Account/Region-dependent features and context lookups will not work,
#     # but a single synthesized template can be deployed anywhere.

#     # Uncomment the next line to specialize this stack for the AWS Account
#     # and Region that are implied by the current CLI configuration.

#     #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

#     # Uncomment the next line if you know exactly what Account and Region you
#     # want to deploy the stack to. */

#     #env=cdk.Environment(account='123456789012', region='us-east-1'),

#     # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
#     )

# app.synth()
