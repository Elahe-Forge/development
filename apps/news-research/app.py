#!/usr/bin/env python3

from aws_cdk import App, Tags, Environment, DefaultStackSynthesizer

from news_research.news_research_stack import NewsResearchStack
# from news_evaluation.news_evaluation_stack import NewsEvaluationStack


app = App()

env_name = app.node.try_get_context("env")
env_context = app.node.try_get_context(env_name)

account = env_context["account"]
region = env_context["region"]
bucket_name = env_context["file_assets_bucket_name"]
team = env_context["team"]

env = Environment(account=account, region=region)

if env_name == "prod":
    role_arn = f"arn:aws:iam::{account}:role/data-science-news-cdk"
    synthesizer = DefaultStackSynthesizer(
        deploy_role_arn = role_arn,
        cloud_formation_execution_role = role_arn,
        file_asset_publishing_role_arn = role_arn,
        image_asset_publishing_role_arn = role_arn,
        file_assets_bucket_name = bucket_name
    )
else:
    synthesizer=DefaultStackSynthesizer(file_assets_bucket_name=bucket_name)

my_stack = NewsResearchStack(app, f"data-science-news-automation-{env_name}", 
                    env_name = env_name,
                    env_account = account,
                    env_region = region,
                    env=env,
                    synthesizer=synthesizer
)
Tags.of(my_stack).add("team", team)

# news_evaluation_stack = NewsEvaluationStack(app, "news-evaluation",
#                     env=env,
#                     synthesizer=DefaultStackSynthesizer(
#                         file_assets_bucket_name=bucket_name
#                     ))
# Tags.of(news_evaluation_stack).add("team", team)

app.synth()


