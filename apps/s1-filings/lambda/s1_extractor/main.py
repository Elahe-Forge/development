
"""
Processes messages from the SQS queue. 
Access the html files in S3.
Extracts S1 lockup info and stores in S3 and FDP Aurora instance.
"""

import os
import boto3
import logging
import pandas as pd
import re
import json
from lxml import etree
from io import BytesIO
from snowflake_client import SnowflakeClient, SnowflakeCredentials
from botocore.exceptions import ClientError


INPUT_PREFIX = 'raw'
OUTPUT_PREFIX = 'output'


# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def extract_lockup(html_texts):
    pattern = r"(As\s+(filed\s+with|confidentially\s+submitted\s+to)\s+)?Securities\s+and\s+Exchange\s+Commission\s+on\s+((\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|([A-Za-z]+\s*\d{1,2}\s*,\s*\d{4}))"

    try:
        match = re.search(pattern, html_texts)
        date_part = None
        if match:
            date_part = match.group(3) if match.group(3) else match.group(4)
            logger.info(f"Extracted date_part: {date_part}")

        formatted_date = None
        # Clean the extracted date part, if found
        if date_part:
            cleaned_txt = clean_text(date_part)
            logger.info(f"Cleaned date_part: {cleaned_txt}")

            # Convert the cleaned text to a datetime object MM/DD/YYYY
            formatted_date = pd.to_datetime(cleaned_txt, errors='coerce')
            if pd.notnull(formatted_date):
                formatted_date = formatted_date.strftime('%m/%d/%Y')

    except Exception as e:
        logger.error(f"An error occurred while extracting or formating the lockup date: {str(e)}")

    return formatted_date


def parse_html(html_content):

    # Convert the HTML content to bytes if it is a string
    if isinstance(html_content, str):
        html_content = html_content.encode('utf-8')

    parser = etree.HTMLParser()
    tree = etree.fromstring(html_content, parser)
    html_nodes = tree.xpath("//p | //h1 | //h2 | //h3 | //h4 | //h5 | //h6 | //li | //b | //i | //u | //section | //div | //span")

    # Extract the text content of each node
    html_texts = ["".join(node.itertext()).strip() for node in html_nodes]

    return html_texts


def clean_text(text):
    pattern = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),?\s*\d{1,2}:\d{2}\s*[APM]*"

    cleaned_text = re.sub(pattern, '', text)

    return cleaned_text



def persist_s1_s3(s1_filing_df, s1_output_bucket):
    try:
        parquet_file_key = f'{OUTPUT_PREFIX}/' + s1_filing['s3_file_path'].removeprefix(f'{INPUT_PREFIX}/').removesuffix('.html') + '.parquet'

        buffer = BytesIO()
        s1_filing_df.to_parquet(buffer, engine='pyarrow', index=False)

        s3.put_object(Bucket=s1_output_bucket, Key=parquet_file_key, Body=buffer.getvalue())

        logger.info(f"Successfully uploaded S-1 Parquet file to S3: {parquet_file_key}")

    except Exception as e:
        logger.error(f"Error occurred while saving S-1 Parquet file to S3: {str(e)}")


def get_from_secret_namager(secret_arn, region_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_arn
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


def persist_s1_snowflake(creds, secret_credentials, s1_filing_df):
    try:
        snowflake_credentials = SnowflakeCredentials(
            account=creds["account"],
            user=secret_credentials["snowflake_svc_data_science_username"],
            private_key=secret_credentials["snowflake_svc_data_science_user_private_key"],
            private_key_passphrase=creds["private_key_passphrase"],
            warehouse=creds["warehouse"],
            database=creds["database"],
            db_schema=creds["db_schema"],
        )

        client = SnowflakeClient(snowflake_credentials)

        temp_table = "temp_s1_fillings_data_ops_fields_extraction"
        db_schema = creds["db_schema"]
        table_name = creds["table_name"]

        query = f"""
            MERGE INTO {db_schema}.{table_name} AS target
            USING {temp_table} AS source
            ON target.ACCESSION_NUMBER = source.ACCESSION_NUMBER
            WHEN MATCHED THEN
                UPDATE SET 
                    target.COMPANY_NAME = source.COMPANY_NAME,
                    target.CIK = source.CIK,
                    target.URL = source.URL,
                    target.PUBLISHED_DATETIME = source.PUBLISHED_DATETIME,
                    target.FORM_TYPE = source.FORM_TYPE,
                    target.S3_FILE_PATH = source.S3_FILE_PATH,
                    target.FILED_DATE = source.FILED_DATE
            WHEN NOT MATCHED THEN
                INSERT (ACCESSION_NUMBER, COMPANY_NAME, CIK, URL, PUBLISHED_DATETIME, FORM_TYPE, S3_FILE_PATH, FILED_DATE)
                VALUES (source.ACCESSION_NUMBER, source.COMPANY_NAME, source.CIK, source.URL, source.PUBLISHED_DATETIME, source.FORM_TYPE, source.S3_FILE_PATH, source.FILED_DATE);
        """
        client.merge(s1_filing_df, temp_table_name= temp_table, target_table_name = table_name, merge_query=query)

        logger.info(f"Successfully uploaded S-1 filings to Snowflake table: {table_name}")

        results_query = 'select * from s1_fillings.data_ops_fields_extraction limit 10'
        results = client.fetchall(results_query)
        logger.info(f"Read results: {results}")

        # Close the session
        client.close()
    
    except Exception as e:
        logger.error(f"Error occurred while saving S-1 filings to Snowflake: {str(e)}")



def handler(event, context):

    s1_bucket = os.environ['S1_FILINGS_BUCKET']
    secret_arn = os.environ['SECRET_ARN']
    region_name = os.environ['REGION_NAME']

    snowflake_creds = os.environ['SNOWFLAKE_CREDENTIALS']

    # Each record is one SQS message to parse
    for record in event['Records']:
        logger.info(f"Raw message body: {record['body']}")

        message_body = json.loads(record['body']) # body is the actual content of the message that is enqueued in the parent Lambda function

        s1_filing = message_body['s1_filing']

        logger.info(f"s1_filing: {s1_filing}")

        try:
            # Fetch the HTML file from the S3 bucket
            response = s3.get_object(Bucket=s1_bucket, Key=s1_filing['s3_file_path'])
            logger.info(f"Successfully retrieved HTML file: {s1_filing['s3_file_path']}")

            html_content = response['Body'].read().decode('utf-8')  # Raw HTML content as string
            html_texts = parse_html(html_content)

            html_texts_cleaned = clean_text(" ".join(html_texts))

            s1_filing['filed_date'] = extract_lockup(html_texts_cleaned)
            logger.info(f"The lockup date for {s1_filing['company_name']}: {s1_filing['filed_date']}")
            
            s1_filing_df = pd.DataFrame([s1_filing])
            persist_s1_s3(s1_filing_df, s1_output_bucket)

            secret_credentials = get_from_secret_namager(secret_arn, region_name)
            persist_s1_snowflake(snowflake_creds, secret_credentials, s1_filing_df)

        
        except s3.exceptions.NoSuchKey as e:
            logger.error(f"File not found in S3: {s1_filing['s3_file_path']}. Error: {str(e)}")
        except Exception as e:
            logger.error(f"An error occurred while processing the file {s1_filing['s3_file_path']}: {str(e)}")

