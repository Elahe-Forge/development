
"""
Processes messages from the SQS queue. 
Fetches and stores news for each issuer received in the message.
"""

import os
import boto3
import datetime
from botocore.exceptions import ClientError
import logging
import pandas as pd
from bs4 import BeautifulSoup
import io 
import re
import requests
import uuid
from llm_handler import GPTProcessor, ClaudeProcessor
import json

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Get the news from the url and strip out all html returning raw text
#
def get_raw_news_text(url : str) -> str: # throws http error if problems w/request
   # Send a GET request to the URL
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception if there was an error
        
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract all text from the parsed HTML
        text = soup.get_text(separator=" ")

        # Remove leading/trailing white spaces and extra line breaks
        text = text.strip()
        
        # Replace newlines and repeated newlines with a single space
        text = re.sub(r'\n+', ' ', text)
        
        # Replace duplicate spaces with a single space
        text = re.sub(r' +', ' ', text)
        logger.debug(f'raw news:{text}')
        return text
    except requests.exceptions.RequestException as e:
        logger.error(f'Error fetching news text from {url}: {e}')
        return None


    
# Intent was to make lambda reusable for different source types
# only DynamoDB is supported    
def get_issuer_items(records : dict, source_type : str) -> dict:
    if source_type != 'dynamodb':
        raise Exception(f'source type: {source_type} not supported')

    news_records = []
    for record in records:
        try:
            if record['eventName'] != 'REMOVE':
                sequence_number = record[source_type]['SequenceNumber']
                company_name_link_date = record[source_type]['Keys']['company_name_link_date']['S']
                issuer = record[source_type]['NewImage']['issuer_name']['S']
                news_date = record[source_type]['Keys']['date']['S']
                news_title = record[source_type]['NewImage']['title']['S']
                news_source = record[source_type]['NewImage']['source']['S']
                news_url = record[source_type]['NewImage']['link']['S']


                news_records.append({'sequence_number':sequence_number,
                                     'company_name_link_date':company_name_link_date,
                                        'issuer':issuer,
                                        'news_date':news_date,
                                        'news_title':news_title,
                                        'news_source':news_source,
                                        'news_url':news_url})
            
        except Exception as e:
            logger.error(f'problem with record: {record}\nerror{e}')
    return news_records

def group_records_by_issuer(records):
    grouped_records = {}
    for record in records:
        issuer = record['issuer']
        if issuer not in grouped_records:
            grouped_records[issuer] = []
        grouped_records[issuer].append(record)
    return grouped_records

# To persist news analysis to S3 as Parquet
def persist_news_analysis(news_records, s3_bucket, model_handle, issuer):
    s3_client = boto3.client('s3')

    if len(news_records) > 0:
        for record in news_records:
            try:
                issuer_name = issuer.replace(" ", "_").lower()  # Replace spaces with underscores and convert to lowercase
                timestamp = datetime.datetime.now()
                unique_id = uuid.uuid4()  # Generate a unique identifier to ensure uniqueness
                
                df = pd.DataFrame([record])
                parquet_buffer = io.BytesIO()
                df.to_parquet(parquet_buffer, index=False)

                s3_prefix = model_handle + "-" + timestamp.strftime("%Y%m%d")  
                s3_object_key = f'news-articles/{s3_prefix}/{issuer_name}/news_record_{timestamp.strftime("%Y%m%d%H%M%S%f")}_{unique_id}.parquet'
                s3_client.put_object(Bucket=s3_bucket, Key=s3_object_key, Body=parquet_buffer.getvalue())
                
                logger.info(f"Persisted record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}' with key '{s3_object_key}'")
            except ClientError as e:
                logger.error(f"Failed to persist record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error occurred while persisting record for issuer '{issuer_name}': {e}")
    else:
        logger.info("No records to persist")

def load_state(s3_bucket):
    try:
        response = s3_client.get_object(Bucket=s3_bucket, Key='state.json')
        return json.loads(response['Body'].read().decode('utf-8'))
    except s3_client.exceptions.NoSuchKey:
        return []

def update_state(s3_bucket, processed_issuers):
    s3_client.put_object(Bucket=s3_bucket, Key='state.json', Body=json.dumps(processed_issuers))

def trigger_next_invocation(context, s3_bucket, processed_issuers, event):
    update_state(s3_bucket, processed_issuers)  # Ensure state is updated before reinvocation
    lambda_client.invoke(
        FunctionName=context.function_name,
        InvocationType='Event',
        Payload=json.dumps(event)
    )
    logger.info('Reinvoked lambda due to imminent timeout.')

def process_records(records, metrics, llm_processor, model_name, model_version):
    processed_records = []
    for news_record in records:
        try:
            raw_news_text = get_raw_news_text(news_record['news_url'])
            if raw_news_text:
                for metric in metrics:
                    result = llm_processor.process_metric(metric, raw_news_text, source=news_record.get('news_source', ''))
                    news_record[metric] = result
                    logger.info(f"Metric: {metric}: {news_record[metric]}")

                news_record['model_name'] = model_name
                news_record['model_version'] = model_version
                news_record['raw'] = raw_news_text
            processed_records.append(news_record)
        except Exception as e:
            logger.error(f'Error processing news record: {news_record}, error: {e}')
    return processed_records

def initialize_llm_processor(model_name, model_handle):
    if model_name.lower() == 'openai':
        return GPTProcessor(model_handle)
    elif model_name.lower() == 'anthropic.claude':
        return ClaudeProcessor(model_handle)
    else:
        raise ValueError(f'Unsupported LLM type: {model_name}') 

def handler(event, context):
    s3_bucket = os.environ['S3_BUCKET']
    model_name = os.environ['MODEL_NAME']
    model_version = os.environ['MODEL_VERSION']
    model_handle = f"{model_name}-{model_version}"

    metrics = ["summary", "reliability", "sentiment", "relevance", "controversy", "tags"]
    remaining_time = context.get_remaining_time_in_millis

    # Load processed issuers from state.json in S3
    processed_issuers = load_state(s3_bucket)

    # Fetch news records and group them by issuer
    news_records = get_issuer_items(event['Records'], 'dynamodb')
    grouped_records = group_records_by_issuer(news_records)

    # Initialize the appropriate LLM processor based on the model_name
    llm_processor = initialize_llm_processor(model_name, model_handle)

    for issuer, records in grouped_records.items():
        if issuer in processed_issuers:
            continue  # Skip already processed issuers

        if remaining_time() < 120000:  # If less than 2 minutes remain
            trigger_next_invocation(context, s3_bucket, processed_issuers, event)
            return {'status': 'Continuation triggered due to timeout risk'}

        processed_records = process_records(records, metrics, llm_processor, model_name, model_version)
        persist_news_analysis(processed_records, s3_bucket, model_handle, issuer)
        processed_issuers.append(issuer)
        update_state(s3_bucket, processed_issuers)  # Update state after each issuer is processed

    return {'status': 'Processing complete'}
