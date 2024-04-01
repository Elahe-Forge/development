"""
Fetch Data and Push to SQS
"""

import json
import boto3
import os
import time
import logging
import pandas as pd
from pyathena import connect

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def query_athena_to_dataframe(query, database, output_location):
    """
    Executes an SQL query on Athena and loads the results into a Pandas DataFrame.
    """

    conn = connect(s3_staging_dir=output_location)  

    df = pd.read_sql(query, conn)
    return df



def lambda_handler(event, context):

    athena_database = os.environ['ATHENA_DATABASE']
    athena_table = os.environ['ATHENA_TABLE']
    athena_output_location = os.environ['S3_OUTPUT_LOCATION']
    athena_query = f"SELECT * FROM {athena_table} limit 10"

    sqs_client = boto3.client('sqs')
    sqs_queue_url = os.environ['EVALUATION_QUEUE_URL']

    # Query Athena and load the results into a DataFrame
    df = query_athena_to_dataframe(athena_query, athena_database, athena_output_location)

    # Iterate over the DataFrame rows
    for index, row in df.iterrows():
        issuer_name = row['issuer_name']  
        logger.info(f"issuer_name: {issuer_name}")

        """
        article_date  
        article_title
        article_summary
        article_tags
        article_raw_text
        ll (text)
        model_version
        article_url
        """
             
        try:
            payload = {'company_name': issuer_name}

            # Send message to SQS queue
            sqs_client.send_message(QueueUrl=sqs_queue_url, MessageBody=json.dumps(payload))
            
            # issuer_count += 1

            logger.info(f"Enqueued message for {issuer_name} in SQS")

        except Exception as e:
            logger.error(f"Error enqueuing message for {issuer_name}: {str(e)}")


    return {
        'statusCode': 200,
        'body': json.dumps('Evaluation Data sent to SQS')
    }


