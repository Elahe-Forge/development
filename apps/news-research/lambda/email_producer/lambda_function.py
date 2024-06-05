"""
Send 2 emails, 1 for updated news of issuers, and another for news of new issuers
"""

import boto3
import pandas as pd
from io import BytesIO
import os
from datetime import datetime, timedelta
import base64
import logging

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("Email service started")

    s3_client = boto3.client('s3')
    ses_client = boto3.client('ses')
    bucket_name = os.getenv('S3_NEWS_OUTPUT_LOCATION')
    parent_prefix = "news-articles/"

    # Determine the date range for the last week
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    date_format = "%Y%m%d"

    # Retrieve the list of objects in the bucket
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=parent_prefix, Delimiter='/')  

    data_frames = {'s3': [], 'api': []}  

    for page in pages:
        for prefix in page.get('CommonPrefixes', []):
            folder_name = prefix['Prefix']
            # Check if folder name matches expected pattern and date
            if '-s3' in folder_name or '-api' in folder_name:
                date_part = folder_name.split('-s3')[0].split('-api')[0].split('-')[-1]  # Extract the date part
                try:
                    folder_date = datetime.strptime(date_part, date_format)
                    if start_date <= folder_date <= end_date:
                        prefix_key = 's3' if '-s3' in folder_name else 'api'
                        collect_parquet_files(s3_client, bucket_name, folder_name, data_frames[prefix_key])
                except ValueError as e:
                    logger.error(f"Error parsing date from folder name {folder_name}: {str(e)}")
                    continue

 
    # Send emails for each prefix
    for key, dfs in data_frames.items():
        if dfs:
            combined_df = pd.concat(dfs)
            send_email(ses_client, combined_df, key)

def collect_parquet_files(s3_client, bucket, prefix, data_frames_list):
    subfolder_pages = s3_client.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=prefix)
    for page in subfolder_pages:
        for item in page.get('Contents', []):
            if item['Key'].endswith('.parquet'):
                try:
                    response = s3_client.get_object(Bucket=bucket, Key=item['Key'])
                    parquet_file = response['Body'].read()
                    df = pd.read_parquet(BytesIO(parquet_file))
                    data_frames_list.append(df)
                except Exception as e:
                    logger.error(f"Failed to process file {item['Key']}: {str(e)}")




def send_email(ses_client, dataframe, prefix):
    
    # Convert DataFrame to Excel for attachment
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False)
    excel_buffer.seek(0)
    attachment = excel_buffer.getvalue()

    # Base64 encode the attachment
    encoded_attachment = base64.b64encode(attachment).decode('utf-8')
    try:
        # Prepare and send the email with the attachment
        response = ses_client.send_raw_email(
            Source='your_verified_email@example.com',
            Destinations=['verified_recipient_email@example.com'],
            RawMessage={
                'Data': f"""
                From: your_verified_email@example.com
                To: verified_recipient_email@example.com
                Subject: Consolidated Data Report for {prefix}
                MIME-Version: 1.0
                Content-Type: multipart/mixed; boundary="simple-boundary"

                --simple-boundary
                Content-Type: text/plain

                Here is the consolidated data report for {prefix}.

                --simple-boundary
                Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;
                Content-Disposition: attachment; filename="consolidated_{prefix}.xlsx"
                Content-Transfer-Encoding: base64

                {encoded_attachment}
                --simple-boundary--
                """
            }
        )
        logger.info(f"Email sent successfully with consolidated data for {prefix}.")

    except Exception as e:
        logger.error(f"Failed to send email for {prefix}: {str(e)}")
