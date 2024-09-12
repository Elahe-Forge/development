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

role_arn = f"arn:aws:iam::{account}:role/coi-reader-cdk-{env_name}"

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
