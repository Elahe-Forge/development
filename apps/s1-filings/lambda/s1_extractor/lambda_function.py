
"""
Processes messages from the SQS queue. 
Access the html files in S3.
Extracts S1 lockup info and stores in S3 and RDS-Postgres.
"""

import os
import boto3
import logging
import pandas as pd
import re
import json
from lxml import etree
from io import BytesIO


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



def persist_s1_s3(s1_filing, s1_output_bucket):

    try:        
        df = pd.DataFrame([{
            'company_name': s1_filing['company_name'],
            'cik': s1_filing['cik'],
            'accession_number': s1_filing['accession_number'],
            'url': s1_filing['url'],
            'published_datetime': s1_filing['published_datetime'],
            'form_type': s1_filing['form_type'],
            's3_file_path': s1_filing['s3_file_path'],
            'filed_date': s1_filing['filed_date']
        }])
       
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', index=False)

        parquet_file_key = s1_filing['s3_file_path'].replace('.html', '.parquet')

        s3.put_object(Bucket=s1_output_bucket, Key=parquet_file_key, Body=buffer.getvalue())
        
        logger.info(f"Successfully uploaded S-1 Parquet file to S3: {parquet_file_key}")
    
    except Exception as e:
        logger.info(f"Error occurred while saving S-1 Parquet file to S3: {str(e)}")


def execute_sql(sql, parameters, database_name, db_cluster_arn, secret_arn):
    rds_client = boto3.client('rds-data')
    
    try:
        response = rds_client.execute_statement(
            resourceArn=db_cluster_arn,
            secretArn=secret_arn,
            database=database_name,
            sql=sql,
            parameters=parameters
        )
        return response
    except Exception as e:
        logger.error(f"Failed to execute SQL: {str(e)}")
        raise


def persist_s1_postgres(s1_filing, db_cluster_arn, database_name, secret_arn):

    try:   
        sql = """
        INSERT INTO s1_filings.data_ops_fields_extraction 
        (accession_number, company_name, cik, url, published_datetime, form_type, s3_file_path, filed_date)
        VALUES (:accession_number, :company_name, :cik, :url, CAST(:published_datetime AS TIMESTAMPTZ), :form_type, :s3_file_path, CAST(:filed_date AS DATE));
        """

        parameters = [
            {'name': 'accession_number', 'value': {'stringValue': s1_filing['accession_number']}},
            {'name': 'company_name', 'value': {'stringValue': s1_filing['company_name']}},
            {'name': 'cik', 'value': {'stringValue': s1_filing['cik']}},
            {'name': 'url', 'value': {'stringValue': s1_filing['url']}},
            {'name': 'published_datetime', 'value': {'stringValue': s1_filing['published_datetime']}},
            {'name': 'form_type', 'value': {'stringValue': s1_filing['form_type']}},
            {'name': 's3_file_path', 'value': {'stringValue': s1_filing['s3_file_path']}},
            {'name': 'filed_date', 'value': {'stringValue': s1_filing['filed_date']} if s1_filing['filed_date'] else {'isNull': True}}
        ]
        
        response = execute_sql(sql, parameters, database_name, db_cluster_arn, secret_arn)
        logger.info(f"Inserted row for {s1_filing['company_name']} - Response: {response}")
    
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e):
            logger.warning(f"Duplicate entry detected for {s1_filing['accession_number']}. Skipping insertion.")
        else:
            logger.error(f"Error in persisting data to PostgreSQL: {str(e)}")
            raise


def handler(event, context):

    s1_html_bucket = os.environ['S1_FILINGS_HTML_BUCKET']
    s1_output_bucket = os.environ['S3_S1_OUTPUT_BUCKET']
    db_cluster_arn = os.environ['DB_CLUSTER_ARN']
    database_name = os.environ['DATABASE_NAME']
    secret_arn = os.environ['SECRET_ARN']
    
    
    # Each record is one SQS message to parse
    for record in event['Records']:
        logger.info(f"Raw message body: {record['body']}")

        message_body = json.loads(record['body']) # body is the actual content of the message that is enqueued in the parent Lambda function

        s1_filing = message_body['s1_filing']
        
        logger.info(f"s1_filing: {s1_filing}")

        try:
            # Fetch the HTML file from the S3 bucket
            response = s3.get_object(Bucket=s1_html_bucket, Key=s1_filing['s3_file_path'])
            logger.info(f"Successfully retrieved HTML file: {s1_filing['s3_file_path']}")

            html_content = response['Body'].read().decode('utf-8')  # Raw HTML content as string
            html_texts = parse_html(html_content)

            html_texts_cleaned = clean_text(" ".join(html_texts))
            
            s1_filing['filed_date'] = extract_lockup(html_texts_cleaned)
            logger.info(f"The lockup date for {s1_filing['company_name']}: {s1_filing['filed_date']}")
            
            persist_s1_s3(s1_filing, s1_output_bucket)
            persist_s1_postgres(s1_filing, db_cluster_arn, database_name, secret_arn)
            
        
        except s3.exceptions.NoSuchKey as e:
            logger.error(f"File not found in S3: {s1_filing['s3_file_path']}. Error: {str(e)}")
        except Exception as e:
            logger.error(f"An error occurred while processing the file {s1_filing['s3_file_path']}: {str(e)}")

        