
"""
Processes messages from the SQS queue. 
Fetches and stores (DynamoDB) and sends (SQS) news for each issuer received in the message.
"""

import os
import boto3
import json
from datetime import datetime, timedelta
from serpapi import GoogleSearch
from botocore.exceptions import ClientError
import logging
from dateutil.relativedelta import relativedelta
import re


# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

def get_serpapi_secret():
    """
    Extract secret key for SerpAPI.
    """

    secret_name = "data-science-and-ml-models/serpapi_token"
    region_name = "us-west-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    secret = get_secret_value_response['SecretString']

    return secret

def get_trusted_sites():
    """
    Fetch the list of trusted sources of News from SSM Parameter Store.
    """
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(
            Name='/data-science-and-ml-models/trusted_sites',
            WithDecryption=True
        )
        trusted_sites = response['Parameter']['Value'].split(',')
        return trusted_sites
    except ClientError as e:
        logger.error(f"Error fetching trusted sites from SSM: {e}")
        return []

def get_google_news(issuer_name, number_of_articles, secret, only_trusted_sites):
    """
    Fetch news for each company using SerpAPI.
    """
    try:
        params = {
            "engine": "google",
            "google_domain": "google.com",
            "q": issuer_name + " company",
            "tbm": "nws",
            "num": number_of_articles,
            "as_qdr": "y",  # last year
            "api_key": secret['SERPAPI_API_KEY']
        }
        
        # Add trusted sites to the query if only_trusted_sites is 'Y'
        if only_trusted_sites == 'Y':
            trusted_sites = get_trusted_sites()    
            sites_query = " OR ".join([f"site:{site}" for site in trusted_sites])
            params["q"] += f" ({sites_query})"
        
        search = GoogleSearch(params)
        results = search.get_dict()        
        return results.get("news_results", [])
    
    except Exception as e:
        # Log any exception that occurs during invocation
        logger.error(f"Error fetching news for {issuer_name}: {e}")
        return []


def convert_relative_date_to_actual(input_date: str) -> str:
    """
    Convert a relative date like '3 weeks ago', '13 hours ago', '29 minutes ago', '2 months ago' or 'Jul 29, 2015' 
    to an actual date in 'MM/DD/YYYY' format.
    """
    try:
        current_date = datetime.now()
        patterns = {
            'seconds': r'(\d+)\s+seconds? ago',
            'minutes': r'(\d+)\s+minutes? ago',
            'hours': r'(\d+)\s+hours? ago',
            'days': r'(\d+)\s+days? ago',
            'weeks': r'(\d+)\s+weeks? ago',
            'months': r'(\d+)\s+months? ago',
            'years': r'(\d+)\s+years? ago'
        }

        for unit, pattern in patterns.items():
            match = re.search(pattern, input_date, re.IGNORECASE)
            if match:
                amount = int(match.group(1))
                if unit == 'seconds':
                    return (current_date - timedelta(seconds=amount)).strftime("%Y-%m-%d")
                elif unit == 'minutes':
                    return (current_date - timedelta(minutes=amount)).strftime("%Y-%m-%d")
                elif unit == 'hours':
                    return (current_date - timedelta(hours=amount)).strftime("%Y-%m-%d")
                elif unit == 'days':
                    return (current_date - timedelta(days=amount)).strftime("%Y-%m-%d")
                elif unit == 'weeks':
                    return (current_date - timedelta(weeks=amount)).strftime("%Y-%m-%d")
                elif unit == 'months':
                    return (current_date - relativedelta(months=amount)).strftime("%Y-%m-%d")
                elif unit == 'years':
                    return (current_date - relativedelta(years=amount)).strftime("%Y-%m-%d")
        
        # If the input is similar to 'Jul 29, 2015'
        actual_date = datetime.strptime(input_date, "%b %d, %Y") 
        return actual_date.strftime("%Y-%m-%d")
    
    except Exception as e:
            logger.error(f"Error getting actual date: {e}")
            return None


def send_to_sqs(queue_url, message_body):
    """
    Send message to SQS queue.
    """    
    try:
        response = sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
        logger.info(f"Message sent to SQS with message ID: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Failed to send message to SQS: {e}")


def store_in_dynamodb(data, table):
    """
    Store the fetched news items in the DynamoDB table with conditional writes to prevent duplicates.
    """
    try:
        data['company_name_link_date'] = f"{data['slug']}-{data['link']}-{data['date']}"
        response = table.put_item(
            Item=data,
            ConditionExpression='attribute_not_exists(company_name_link_date)'
        )

        logger.info(f"Data stored in DynamoDB successfully for {data['issuer_name']}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.info(f"Data already exists, skipped: {data['company_name_link_date']}")
            return False
        else:
            logger.error(f"Error storing news data in DynamoDB for {data['issuer_name']}: {e}")
            return False


def process_news(news_results, issuer_name, sqs_url, dynamodb_table, slug, company_id, get_summary, triggered_by):
    """
    Process multiple news_results: check existence, store new in S3, and send to SQS.
    """
    enqueued_items = []
    for item in news_results:
        try:
            item['date'] = convert_relative_date_to_actual(item.get('date'))           
            item['issuer_name'] = issuer_name
            item['slug'] = slug
            item['company_id'] = company_id
            item['get_summary'] = get_summary
            item['triggered_by'] = triggered_by

            if store_in_dynamodb(item.copy(), dynamodb_table):
                enqueued_items.append(item)  # Add to the list of items to send to SQS
                logger.info(f"Stored in DynamoDB and enqueued for SQS for {issuer_name}")

        except Exception as e:
            logger.error(f"Error processing news for {issuer_name}: {e}")

    if enqueued_items:
        send_to_sqs(sqs_url, {'news_items': enqueued_items})
        logger.info(f"Enqueued {len(enqueued_items)} news items for {issuer_name} in SQS")


def handler(event, context):
    serpapi_secret_key = json.loads(get_serpapi_secret())

    sqs_url = os.environ['LLM_CONSUMER_QUEUE_URL']
    dynamodb_table = dynamodb.Table(os.environ['NEWS_TABLE'])
    only_trusted_sites = os.environ['ONLY_TRUSTED_SITES'] # 'Y' or 'N'
    
    # Each record is one SQS message to parse
    for record in event['Records']:
        message_body = json.loads(record['body']) # body is the actual content of the message that is enqueued in the parent Lambda function
        
        issuer_name = message_body['issuer_name']
        slug = message_body['slug']
        company_id = message_body['company_id']
        number_of_articles = message_body['number_of_articles']
        get_summary = message_body['get_summary'] 
        triggered_by = message_body['triggered_by']
        
        logger.info(f"issuer_name: {issuer_name}, slug: {slug}, company_id: {company_id}")

        news_results = get_google_news(issuer_name, number_of_articles, serpapi_secret_key, only_trusted_sites)
        logger.info(f"News results for {issuer_name}: {news_results}")
        
        process_news(news_results, issuer_name, sqs_url, dynamodb_table, slug, company_id, get_summary, triggered_by)



        




