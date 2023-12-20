
"""
Scans the DynamoDB table for issuers and enqueue (SQS queue) issuer names if they meet the criteria (last visited more than 24 hours ago)
"""

import os
import boto3
import json
import logging
import datetime



logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    issuers_table = dynamodb.Table(os.environ['ISSUERS_TABLE_NAME'])

    sqs_client = boto3.client('sqs')
    queue_url = os.environ['ISSUER_QUEUE_URL']

    # Determine the type of command (run-all or run-issuer)
    path = event.get('resource')  # Get the path that triggered the Lambda

    issuer_count = 0

    # Logic for 'run-all' command
    if path == '/run-all': 
        # Enqueue all issuers

        # Scan the table for all issuers
        response = issuers_table.scan()
        for issuer in response['Items']:
            
            last_visited = issuer.get('last_visited')
            issuer_name = issuer['issuer_name']    
            logger.info(f"issuer_name {issuer_name} and last_visited {last_visited}")

            # Check if last_visited is empty or older than 24 hours
            if not last_visited or (datetime.datetime.now() - datetime.datetime.fromisoformat(last_visited)).total_seconds() > 86400:
                
                try:
                    payload = {'company_name': issuer_name}

                    # Send message to SQS queue
                    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
                    issuer_count += 1
                    logger.info(f"Enqueued message for {issuer_name} in SQS")

                except Exception as e:
                    logger.error(f"Error enqueuing message for {issuer_name}: {str(e)}")

    elif path == '/run-issuer': # Logic for 'run-issuer' command

        # Extract issuer from the body
        issuer_name = event.get('body', '').strip()
        if issuer_name:
            try:
                payload = {'company_name': issuer_name}
                sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
                issuer_count = 1
                logger.info(f"Enqueued message for {issuer_name} in SQS")
            except Exception as e:
                logger.error(f"Error enqueuing message for {issuer_name}: {str(e)}")
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('Issuer name is required for run-issuer command.')
            }

    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid command.')
        }
    
    # Return a success response
    return {
        'statusCode': 200,
        'body': json.dumps(f'Enqueued N={issuer_count} issuers.')
    }




