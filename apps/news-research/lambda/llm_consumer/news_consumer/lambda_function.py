
"""
Processes messages from the SQS queue. 
Fetches and stores news for each issuer received in the message.
"""

import os
import boto3
import datetime
from botocore.exceptions import ClientError
import logging
from bs4 import BeautifulSoup
import re
import requests
import uuid
from llm_handler import GPTProcessor, ClaudeProcessor
import json
import pandas as pd
import io

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')


def process_records(records, llm_processor, model_name, model_version, s3_news_output_bucket, prompt_version):
    """ Process each news record and persist results. """
    
    metrics = ["reliability", "sentiment", "relevance", "controversy", "tags"]

    for news_record in records:
        try:
            if news_record['get_summary']:
                metrics.insert(0, "summary") 
            
            results = {}
            raw_news_text = get_raw_news_text(news_record['link'])
                            
            for metric in metrics:
                if raw_news_text:
                    results[metric] = llm_processor.process_metric(metric, raw_news_text, source=news_record.get('source', ''))
                else:
                    results[metric] = None
            
            news_record.update(results)
            news_record.update({'model_name': model_name, 'model_version': model_version, 'raw': raw_news_text, 'prompt_version': prompt_version})
            

        except Exception as e:
            logger.error(f'Error processing news record: {news_record}, error: {e}')

        if news_record['triggered_by'] == 's3_excel':
            persist_news_analysis_parquet(news_record, s3_news_output_bucket, f"{model_name}-{model_version}")
    if records[0]['triggered_by'] == 'api_json':
        persist_news_analysis(records, s3_news_output_bucket, f"{model_name}-{model_version}")
    

# Get the news from the url and strip out all html returning raw text
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


def persist_news_analysis(news_records, s3_news_output_bucket, model_handle):
    """ 
    Persist a list of news records to S3 as a single JSON file. 
    """
    if news_records and isinstance(news_records, list):  
        try:
            logger.info(f"Persisting {len(news_records)} news records")

            first_record = news_records[0]
            issuer_name = first_record['issuer_name']
            slug = first_record['slug']
            company_id = first_record['company_id']
            timestamp = datetime.datetime.now()
            unique_id = uuid.uuid4()  # Generate a unique identifier to ensure uniqueness

            json_data = json.dumps(news_records)
            s3_prefix = timestamp.strftime("%Y%m%d") + "-" + model_handle 
            s3_object_key = f'news-articles/{s3_prefix}/{slug}_{company_id}/news_records_{unique_id}.json'
            s3_client.put_object(Bucket=s3_news_output_bucket, Key=s3_object_key, Body=json_data)
            
            logger.info(f"Persisted {len(news_records)} records for issuer '{issuer_name}' to S3 bucket '{s3_news_output_bucket}' with key '{s3_object_key}'")
        except ClientError as e:
            logger.error(f"Failed to persist records for issuer '{issuer_name}' to S3 bucket '{s3_news_output_bucket}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while persisting records for issuer '{issuer_name}': {e}")




def persist_news_analysis_parquet(news_record, s3_news_output_bucket, model_handle):
    """ 
    Persist a news record to S3 as a single Parquet file. 
    """
    if news_record:  
        try:
            logger.info(f"Persisting news records: {news_record}")

            issuer_name = news_record['issuer_name']
            slug = news_record['slug']
            company_id = news_record['company_id']
            timestamp = datetime.datetime.now()
            unique_id = uuid.uuid4()  # Generate a unique identifier to ensure uniqueness

            if isinstance(news_record.get('tags'), list):
                news_record['tags'] = ', '.join(news_record['tags'])  # Join list elements as a string

            df = pd.DataFrame([news_record])
            
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False)
            parquet_buffer.seek(0) 

            s3_prefix = timestamp.strftime("%Y%m%d") + "-" + model_handle 
            s3_object_key = f'news-articles/{s3_prefix}/{slug}_{company_id}/news_records_{unique_id}.parquet'
            
            s3_client.put_object(Bucket=s3_news_output_bucket, Key=s3_object_key, Body=parquet_buffer.getvalue())
            
            logger.info(f"Persisted records for issuer '{issuer_name}' to S3 bucket '{s3_news_output_bucket}' with key '{s3_object_key}'")
        except ClientError as e:
            logger.error(f"Failed to persist records for issuer '{issuer_name}' to S3 bucket '{s3_news_output_bucket}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while persisting records for issuer '{issuer_name}': {e}")


def initialize_llm_processor(model_name, model_handle, s3_news_prompts_bucket, prompt_version):
    if model_name.lower() == 'openai':
        return GPTProcessor(model_handle, s3_news_prompts_bucket, prompt_version)
    elif model_name.lower() == 'anthropic.claude':
        return ClaudeProcessor(model_handle, s3_news_prompts_bucket, prompt_version)
    else:
        raise ValueError(f'Unsupported LLM type: {model_name}') 

def handler(event, context):
    s3_news_output_bucket = os.environ['S3_NEWS_OUTPUT_BUCKET']
    model_name = os.environ['MODEL_NAME']
    model_version = os.environ['MODEL_VERSION']
    model_handle = f"{model_name}-{model_version}"
    s3_news_prompts_bucket = os.environ['S3_NEWS_PROMPTS_BUCKET'] 
    prompt_version = os.environ['PROMPT_VERSION']
    
    # Initialize the appropriate LLM processor based on the model_name
    llm_processor = initialize_llm_processor(model_name, model_handle, s3_news_prompts_bucket, prompt_version)

    for record in event['Records']:
        logger.info(f"Record: '{record}'")
        message_body = json.loads(record['body'])
        
        process_records(message_body['news_items'], llm_processor, model_name, model_version, s3_news_output_bucket, prompt_version)
        

    return {'status': 'Processing complete'}
