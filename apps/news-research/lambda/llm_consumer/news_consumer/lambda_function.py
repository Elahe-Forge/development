
"""
Processes messages from the SQS queue. 
Fetches and stores news for each issuer received in the message.
"""

import os
import boto3
import json
import datetime
from botocore.exceptions import ClientError
import logging

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    for record in event['Records']: 
        logger.info(record['dynamodb'])
    