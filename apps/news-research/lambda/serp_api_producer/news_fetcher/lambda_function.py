
"""
Processes messages from the SQS queue. 
Fetches and stores news for each issuer received in the message.
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


def get_google_news(issuer_name, secret):
    """
    Fetch news for each company using SerpAPI.
    """
    try:
        
        params = {
            "q":  issuer_name + " company",
            "tbm": "nws",
            # "num": 1,
            "api_key": secret['SERPAPI_API_KEY']
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("news_results", [])
    
    except Exception as e:
        # Log any exception that occurs during invocation
        logger.error(f"Error fetching news for {issuer_name}: {e}")
        return []


def convert_relative_date_to_actual(input_date: str) -> str:
    """
    Convert a relative date like '3 weeks ago', '13 hours ago', '2 months ago' or 'Jul 29, 2015' 
    to an actual date in 'MM/DD/YYYY' format.
    """
    try:
        current_date = datetime.now()
        patterns = {
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
                if unit == 'hours':
                    return (current_date - timedelta(hours=amount)).strftime("%Y/%m/%d")
                elif unit == 'days':
                    return (current_date - timedelta(days=amount)).strftime("%Y/%m/%d")
                elif unit == 'weeks':
                    return (current_date - timedelta(weeks=amount)).strftime("%Y/%m/%d")
                elif unit == 'months':
                    return (current_date - relativedelta(months=amount)).strftime("%Y/%m/%d")
                elif unit == 'years':
                    return (current_date - relativedelta(years=amount)).strftime("%Y/%m/%d")
        
        # If the input is similar to 'Jul 29, 2015'
        actual_date = datetime.strptime(input_date, "%b %d, %Y") 
        return actual_date.strftime("%Y/%m/%d")
    
    except Exception as e:
            logger.error(f"Error getting actual date: {e}")
            return None


def store_news(news_results, table, company_name):
    """
    Store the fetched news items in the DynamoDB table.
    """
    for item in news_results:
        try:
            table.put_item(Item={
                'company_name': company_name,
                'position': item.get('position'),
                'link': item.get('link'),
                'title': item.get('title'),
                'source': item.get('source'),
                'date': convert_relative_date_to_actual(item.get('date')),
                'snippet': item.get('snippet'),
                'thumbnail': item.get('thumbnail')
            })
        except Exception as e:
            logger.error(f"Error storing news item in DynamoDB for {company_name}: {e}")


def handler(event, context):

    serpapi_secret_key = json.loads(get_serpapi_secret())

    dynamodb = boto3.resource('dynamodb')
    news_table = dynamodb.Table(os.environ['NEWS_TABLE'])


    # Each record is one SQS message to parse
    for record in event['Records']: 
        message_body = json.loads(record['body']) # body is the actual content of the message that is enqueued in the parent Lambda function
        company_name = message_body['company_name']
    
        news_results = get_google_news(company_name, serpapi_secret_key)
        logger.info(f" news_results {news_results}")
        
        store_news(news_results, news_table, company_name)
        




