#!/bin/bash

# Set the AWS_PROFILE to prod
export AWS_PROFILE=prod

# Deploy the CDK stack with the prod context
cdk deploy data-science-news-automation-prod --context env=prod