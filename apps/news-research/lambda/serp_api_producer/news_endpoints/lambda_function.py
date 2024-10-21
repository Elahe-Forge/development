
"""
Enqueues (SQS queue) issuer names
Get triggered by API Gateway
"""

import os
import boto3
import json
import logging
import time
import pandas as pd
from io import BytesIO

logger = logging.getLogger()
logger.setLevel(logging.INFO)

default_number_of_articles = os.getenv('DEFAULT_NUMBER_OF_ARTICLES')
default_get_summary = os.getenv('DEFAULT_GET_SUMMARY')


def query_athena_and_wait_for_results(query, database, output_location):
    """
    Executes an SQL query on Athena and waits for the result.
    """
    athena_client = boto3.client('athena')

    execution_id = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={'OutputLocation': output_location}
    )['QueryExecutionId']
    

    while True:
        response = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = response['QueryExecution']['Status']['State']
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        time.sleep(1)

    if state != 'SUCCEEDED':
        status = response['QueryExecution']['Status']
        raise Exception(f"Athena query failed: State={state}, Status={status}")
    

    return athena_client.get_query_results(QueryExecutionId=execution_id)


def send_message_to_sqs(payload):
    sqs_client = boto3.client('sqs')
    queue_url = os.environ['ISSUER_QUEUE_URL']
    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))



def validate_positive_integer(value, default):
    try:
        int_val = int(value)
        if int_val > 0:
            return int_val
    except (ValueError, TypeError):
        pass
    return default


def process_run_json(event, number_of_articles, get_summary):
    logger.info(f"Processing JSON data with number_of_articles: {number_of_articles}, get_summary: {get_summary}")
    articles_data = None

    # Extract JSON data from the request body if present
    if 'body' in event and event['body']:
        try:
            articles_data = json.loads(event['body'])
            if not isinstance(articles_data, list) or not all(isinstance(item, dict) for item in articles_data):
                logger.info("Invalid JSON format for articles data.")
                return {
                    'statusCode': 400,
                    'body': json.dumps('Invalid JSON format for articles data.')
                }
        except json.JSONDecodeError:
            logger.info("Invalid JSON provided in the request body.")
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid JSON format.')
            }
    else:
        logger.info("JSON body is required for this endpoint.")
        return {
            'statusCode': 400,
            'body': json.dumps('JSON body is required for this endpoint.')
        }

    logger.info(f"Articles Data: {articles_data}")

    # Iterate over each article and create a payload to send to SQS
    for article in articles_data:
        issuer_name = article.get('name')
        slug = article.get('slug')
        company_id = article.get('company_id')
        payload = {
            'issuer_name': issuer_name,
            'slug': slug,
            'company_id': company_id,
            'number_of_articles': number_of_articles,
            'get_summary': get_summary,
            'triggered_by': 'api_json'
        }
        send_message_to_sqs(payload)

    return {
        'statusCode': 200,
        'body': json.dumps('Messages sent to SQS successfully.')
    }
   

def process_run_s3_excel(event, number_of_articles, get_summary):
    s3_client = boto3.client('s3')
    s3_bucket = os.environ['S3_EXCEL_SHEET_LOCATION']
    
    s3_key_prefix = event.get('body', '').strip().strip('"')  # Extract folder name from the body
    # 'test-05-15-24/'   

    # List objects in the specified folder or the entire bucket
    response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_key_prefix)
    # Check if any objects are found
    if 'Contents' in response:
        try:
            issuer_count = 0
            for item in response['Contents']:
                key = item['Key']
                if key.endswith('.xlsx'):  # Ensure the file is an Excel file
                    # Get the object from S3
                    obj = s3_client.get_object(Bucket=s3_bucket, Key=key)
                    
                    # Read the object as an Excel file into a DataFrame
                    excel_data = obj['Body'].read()
                    df = pd.read_excel(BytesIO(excel_data))
                    
                    # Extract the 'issuerKey' column, assuming it exists
                    if 'issuerKey' in df.columns:
                        for _, row in df.dropna(subset=['issuerKey']).iterrows():
                            issuer_name = row['issuerKey']
                            # slug = row['slug']
                            # company_id = row['company_id']
                            slug = row['issuerKey']
                            company_id = row['issuerKey']
                            payload = {
                                'issuer_name': issuer_name,
                                'slug': slug,
                                'company_id': company_id,
                                'number_of_articles': number_of_articles,
                                'get_summary': get_summary,
                                'triggered_by': 's3_excel'
                            }
                            send_message_to_sqs(payload)
                            issuer_count += 1
                            logger.info(f"Enqueued message for {issuer_name} in SQS")
                    else:
                        logger.info(f"'issuerKey' column not found in {key}")
                        
        except Exception as e:
            logger.error(f'Error processing files: {str(e)}')
        return {
                'statusCode': 200,
                'body': json.dumps(f'Enqueued message for {issuer_count} in SQS')
            }
    else:
        logger.info("No objects found with the specified S3 bucket.")
        return {
            'statusCode': 400,
            'body': json.dumps('No objects found with the specified S3 bucket.')
        }



def handler(event, context):
    logger.info("Triggered by API Gateway")
    # Determine the number_of_articles and whether to get summary of articles
    query_params = event.get('queryStringParameters') or {}
    number_of_articles = validate_positive_integer(query_params.get('number_of_articles'), default_number_of_articles)
    get_summary = query_params.get('get_summary', default_get_summary).lower() == 'true'

    # Determine the type of command (run-all or run-issuer)
    path = event.get('resource')
    if path == '/run-json':
        return process_run_json(event, number_of_articles, get_summary)  
    elif path == '/run-s3':
        return process_run_s3_excel(event, number_of_articles, get_summary)
    else:
        logger.info("Invalid command.")
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid command.')
        }
        

