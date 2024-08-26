#!/bin/bash

# Set the AWS_PROFILE to dev
export AWS_PROFILE=dev

# Deploy the CDK stack with the dev context
cdk deploy data-science-s1-filings-automation-dev --context env=dev
