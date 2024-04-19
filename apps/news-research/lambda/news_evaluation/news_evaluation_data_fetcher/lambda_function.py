"""
Reads parquet files from S3
and distribute them via SQS. 
It is triggered by an API Gateway event.
"""

import boto3
import os
import pandas as pd
import io
import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    s3_client = boto3.client('s3')
    sqs_client = boto3.client('sqs')
    sqs_queue_url = os.environ['EVALUATION_QUEUE_URL']
    s3_bucket = os.environ['S3_BUCKET']

    try:
        # Extract the resource path and request body
        resource_path = event['resource']

        if resource_path == '/run-issuer':
            issuer_name = event['body'].strip().replace(' ', '_')        
            logger.info(f"issuer_name folder: {issuer_name}")
            s3_key_prefix = f"news-articles/{issuer_name}/"

        elif resource_path == '/run-all':
            s3_key_prefix = 'news-articles/'  # List all objects in the bucket
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid resource path'})
            }

        # List objects in the specified folder or the entire bucket
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_key_prefix)
        
        if 'Contents' not in response:
            logger.error("Contents is empty.")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No files found'})
            }

        # Process each object
        for obj in response['Contents']:
            key = obj['Key']

            # Read the Parquet file from S3
            parquet_response = s3_client.get_object(Bucket=s3_bucket, Key=key)
            parquet_file = parquet_response['Body'].read()

            # Convert to DataFrame
            df = pd.read_parquet(io.BytesIO(parquet_file))

            # Convert DataFrame to JSON and send to SQS
            message_body = df.to_json(orient='records')
            sqs_response = sqs_client.send_message(
                QueueUrl=sqs_queue_url,
                MessageBody=message_body
            )

            logger.info(f"Enqueued message for issuer: {df['issuer'][0]} in SQS")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'Processed files for {df['issuer'][0]} in SQS'})
        }

    except Exception as e:
        logger.error(f'Error processing files: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


