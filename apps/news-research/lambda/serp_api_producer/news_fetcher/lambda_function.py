
"""
Processes messages from the SQS queue. 
Fetches and stores news for each issuer received in the message.
"""

import os
import boto3
import json
import datetime
from serpapi import GoogleSearch
from botocore.exceptions import ClientError
import logging

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_serpapi_secret():
    """
    Extract secret key for SerpAPI.
    """

    secret_name = "news-research-data-science"
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
                'date': item.get('date'),
                'snippet': item.get('snippet'),
                'thumbnail': item.get('thumbnail')
            })
        except Exception as e:
            logger.error(f"Error storing news item in DynamoDB for {company_name}: {e}")


def handler(event, context):

    serpapi_secret_key = json.loads(get_serpapi_secret())

    dynamodb = boto3.resource('dynamodb')
    news_table = dynamodb.Table(os.environ['NEWS_TABLE'])
    issuers_table = dynamodb.Table(os.environ['ISSUERS_TABLE_NAME'])


    # Each record is one SQS message to parse
    for record in event['Records']: 
        message_body = json.loads(record['body']) # body is the actual content of the message that is enqueued in the parent Lambda function
        company_name = message_body['company_name']
        # last_visited = message_body['last_visited']
    
        news_results = get_google_news(company_name, serpapi_secret_key)
        logger.info(f" news_results {news_results}")
        
        store_news(news_results, news_table, company_name)
        
        issuers_table.update_item(
            Key={'issuer_name': company_name},
            UpdateExpression='SET last_visited = :val',
            ExpressionAttributeValues={
                ':val': datetime.datetime.now().isoformat()
            }
        )

    return {
        'statusCode': 200,
        'body': json.dumps(f"News updated for for {company_name}")
    }



