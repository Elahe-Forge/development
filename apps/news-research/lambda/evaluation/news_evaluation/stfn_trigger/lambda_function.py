"""
Trigger Step Functions State Machine
"""

import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # Initialize client
    stepfunctions_client = boto3.client('stepfunctions')

    # ARN of the Step Functions state machine
    state_machine_arn = os.environ['STATE_MACHINE_ARN']

    # Get the message from the SQS event
    for record in event['Records']:
        message_body = json.loads(record['body'])
        try:

            # Start the Step Functions state machine execution
            response = stepfunctions_client.start_execution(
                stateMachineArn=state_machine_arn,
                input=json.dumps(message_body)
            )

            # Log the response
            logger.info(f"Started execution: {response['executionArn']}")

        except Exception as e:
            logger.error(f"Error : {str(e)} - - response: {response}")

    return {
        'statusCode': 200,
        'body': json.dumps('Triggered Step Functions successfully')
    }
