
"""
Processes messages from the dead letter queue. 
"""

import json
import logging

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_error(message):
    error_type = message.get('error_type')

    if error_type == 'Timeout':
        logger.error(f"Timeout Error Processed: {message}")
        # Handle timeout-specific logic, such as retrying the operation
    elif error_type == 'InvalidData':
        logger.error(f"Invalid Data Error: {message}")
        # Handle invalid data errors, possibly cleaning data or sending alerts
    else:
        logger.error(f"Unknown Error Type: {message}")

def handler(event, context):
    for record in event['Records']:
        logger.info(f"Received message: {record['body']} from DLQ")
        message_body = json.loads(record['body'])
        source_queue_arn = record['eventSourceARN']

        # Identify the queue from the ARN
        if 'NewsIssuerDLQ' in source_queue_arn:
            logger.info(f"Processing message from Issuer Queue's DLQ: {message_body}")
            
        elif 'NewsLlmConsumerDLQ' in source_queue_arn:
            logger.info(f"Processing message from Consumer Queue's DLQ: {message_body}")
           
        else:
            logger.warning(f"Received message from unknown source: {message_body}")

        handle_error(message_body)
        logger.info(f"Processed message from DLQ: {message_body}")