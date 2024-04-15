"""
Fetch Data and Push to SQS
"""

import boto3
import pandas as pd
import io
from urllib.parse import unquote_plus
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)



def handler(event, context):
    s3_client = boto3.client('s3')
    sqs_client = boto3.client('sqs')
    sqs_queue_url = os.environ['EVALUATION_QUEUE_URL']
    s3_bucket = os.environ['S3_BUCKET']

    for news_record in event['Records']:
        try:
            logger.info(f'Processing news record: {news_record}')
            key = unquote_plus(news_record['s3']['object']['key'])

            # Read the Parquet file from S3
            response = s3_client.get_object(Bucket=s3_bucket, Key=key)
            parquet_file = response['Body'].read()

            # Convert to DataFrame
            df = pd.read_parquet(io.BytesIO(parquet_file))

            # Convert DataFrame to JSON and send to SQS
            message_body = df.to_json(orient='records')
            sqs_response = sqs_client.send_message(
                QueueUrl=sqs_queue_url,
                MessageBody=message_body
            )

            logger.info(f"Enqueued message for issuer: {df['issuer'][0]} in SQS")

        except Exception as e:
            logger.error(f"Error enqueuing message: {str(e)}")

    return {
        'statusCode': 200,
        'body': 'Processed Parquet files and sent data to SQS'
    }
