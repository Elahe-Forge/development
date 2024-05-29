
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


def process_records(records, metrics, llm_processor, model_name, model_version, s3_bucket):
    """ Process each news record and persist results. """
    for news_record in records:
        try:
            raw_news_text = get_raw_news_text(news_record['link'])
            if raw_news_text:
                results = {
                    "summary": "",
                    "reliability": "",
                    "sentiment": "",
                    "relevance": "",
                    "controversy": "",
                    "tags": ""
                }
                for metric in metrics:
                    result = llm_processor.process_metric(metric, raw_news_text, source=news_record.get('source', ''))
                    results[metric] = result
            
                news_record.update(results)
                news_record.update({'model_name': model_name, 'model_version': model_version, 'raw': raw_news_text})
                persist_news_analysis(news_record, s3_bucket, f"{model_name}-{model_version}")

        except Exception as e:
            logger.error(f'Error processing news record: {news_record}, error: {e}')


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


def persist_news_analysis(news_records, s3_bucket, model_handle):
    """ 
    Persist news analysis to S3 as Parquet. 
    """
    if news_records:  
        try:
            logger.info(f"news_records '{news_records}'")
            issuer_name = news_records['issuer_name'].replace(" ", "_").lower()  # Replace spaces with underscores and convert to lowercase
            timestamp = datetime.datetime.now()
            unique_id = uuid.uuid4()  # Generate a unique identifier to ensure uniqueness
            
            df = pd.DataFrame([news_records])
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

    metrics = ["reliability", "sentiment", "relevance", "controversy", "tags"]
    
    # Initialize the appropriate LLM processor based on the model_name
    llm_processor = initialize_llm_processor(model_name, model_handle)

    for record in event['Records']:
        logger.info(f"Record: '{record}'")
        message_body = json.loads(record['body'])
        get_summary = message_body['get_summary'] 
        if get_summary:
            metrics.insert(0, "summary") 
        process_records([message_body['news_item']], metrics, llm_processor, model_name, model_version, s3_bucket)
        

    return {'status': 'Processing complete'}
