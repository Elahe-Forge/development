
"""
Processes messages from the dead letter queue. 
"""

import boto3
import json
import logging
import os

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_email_address(parameter_name):
    ssm_client = boto3.client('ssm')
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    return response['Parameter']['Value']

def subscribe_email_to_sns(sns_client, topic_arn, email):
    response = sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint=email,
        ReturnSubscriptionArn=True
    )
    logger.info(f"Subscribed {email} to {topic_arn} with subscription ARN: {response['SubscriptionArn']}")


def handle_error(message):
    error_type = message.get('error_type')

    if error_type == 'Timeout':
        logger.error(f"Timeout Error Processed: {message}")
        # Handle timeout-specific logic, such as retrying the operation
    elif error_type == 'InvalidData':
        logger.error(f"Invalid Data Error: {message}")
        # Handle invalid data errors
    else:
        logger.error(f"Unknown Error Type: {message}")

def handler(event, context):
    email_parameter_name = os.environ['EMAIL_PARAM']
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    sns_client = boto3.client('sns')
    
    # Fetch email address from Parameter Store
    source_email = get_email_address(email_parameter_name)
    
    # Subscribe email to SNS topic
    subscribe_email_to_sns(sns_client, sns_topic_arn, source_email)

    for record in event['Records']:
        logger.info(f"Received message: {record['body']} from DLQ")
        message_body = json.loads(record['body'])
        source_queue_arn = record['eventSourceARN']

        # Identify the queue from the ARN
        if 'NewsIssuerDLQ' in source_queue_arn:
            logger.info(f"Processing message from Issuer Queue's DLQ: {message_body}")
            subject = "Issuer Queue DLQ Alert"
            
        elif 'NewsLlmConsumerDLQ' in source_queue_arn:
            logger.info(f"Processing message from Consumer Queue's DLQ: {message_body}")
            subject = "LLM Consumer Queue DLQ Alert"
           
        else:
            logger.warning(f"Received message from unknown source: {message_body}")
            subject = "Unknown Queue DLQ Alert"

        handle_error(message_body)
        logger.info(f"Processed message from DLQ: {message_body}")
        
        # Send SNS notification
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(message_body),
            Subject=subject
        )
