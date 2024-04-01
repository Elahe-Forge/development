#!/usr/bin/env python3

from aws_cdk import App, Tags
from aws_cdk import DefaultStackSynthesizer
import aws_cdk

from news_research.news_research_stack import NewsResearchStack
from news_evaluation.news_evaluation_stack import NewsEvaluationStack

env_oregon = aws_cdk.Environment(account="597915789054", region="us-west-2")

app = App()

my_stack = NewsResearchStack(app, "news-research", 
                    env=env_oregon,
                    synthesizer= DefaultStackSynthesizer(
                        file_assets_bucket_name="data-science-cdk"
                        )
)
Tags.of(my_stack).add("team", "orange")

news_evaluation_stack = NewsEvaluationStack(app, "news-evaluation",
                    env=env_oregon,
                    synthesizer=DefaultStackSynthesizer(
                        file_assets_bucket_name="data-science-cdk"
                    ))
Tags.of(news_evaluation_stack).add("team", "orange")

app.synth()

 

