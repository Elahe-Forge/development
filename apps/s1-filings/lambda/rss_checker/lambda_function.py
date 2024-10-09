
"""
Subscribes to SEC RSS and extracts new S1 filings submitted daily.
Saves the html files in S3 and sends message to SQS.
"""

import os
import boto3
import logging
import requests
import feedparser
import re
from io import BytesIO
from botocore.exceptions import ClientError
import json

s3 = boto3.client('s3')

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def fetch_s1_rss(headers):
    rss_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom" 
    
    try:
        with requests.get(rss_url, headers=headers) as response:
            response.raise_for_status()
   
        feed = feedparser.parse(response.content)
        s1_filings = []
        """
            Example entries:
                <entry>
                    <title>S-1/A - Linkhome Holdings Inc. (0002017758) (Filer)</title>
                    <link rel="alternate" type="text/html" href="https://www.sec.gov/Archives/edgar/data/2017758/000121390024083888/0001213900-24-083888-index.htm"/>
                    <summary type="html">
                    &lt;b&gt;Filed:&lt;/b&gt; 2024-10-01 &lt;b&gt;AccNo:&lt;/b&gt; 0001213900-24-083888 &lt;b&gt;Size:&lt;/b&gt; 10 MB
                    </summary>
                    <updated>2024-10-01T13:33:50-04:00</updated>
                    <category scheme="https://www.sec.gov/" label="form type" term="S-1/A"/>
                    <id>urn:tag:sec.gov,2008:accession-number=0001213900-24-083888</id>
                </entry>
        """
        for entry in feed.entries:
            form_type = entry.get('tags')[0].get('term')
                
            if form_type == 'S-1' or form_type == 'S-1/A':
                accession_number, cik, company_name = fetch_accession_cik_company_name(entry)       
                s1_filings.append({
                    'company_name': company_name,
                    'cik': cik,
                    'accession_number': accession_number,
                    'url': entry.link,
                    'published_datetime': entry.updated,
                    'form_type': form_type
                })
        
        return s1_filings

    except Exception as e:
        logger.error(f"Failed to fetch RSS feed: {e}")
        return []


def fetch_accession_cik_company_name(entry):   
    
    try:
        accession_number = None
        cik = None
        company_name = None

        accession_pattern = r"accession-number=(\d{10}-\d{2}-\d{6})"
        accession_match = re.search(accession_pattern, entry.id)

        if accession_match:
            accession_number = accession_match.group(1)
            logger.info(f"Accession Number: {accession_number}")
        else:
            logger.error("No match found for accession number.")

        cik_pattern = r"\((\d{10})\)"
        cik_match = re.search(cik_pattern, entry.title)

        if cik_match:
            cik = cik_match.group(1)
            logger.info(f"CIK: {cik}")
        else:
            logger.error("No match found for CIK.")

        company_name_pattern = r"- (.*?) \("
        company_name_match = re.search(company_name_pattern, entry.title)

        if company_name_match:
            company_name = company_name_match.group(1)
            logger.info(f"Company Name: {company_name}")
        else:
            logger.error("No match found for company name.")

        return accession_number, cik, company_name

    except Exception as e:
        logger.error(f"Failed to fetch accession number and/or CIK: {e}")
        return None, None, None
            

def fetch_s1_primary_document(headers, cik, accession_number):
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
               
        try:
            response = requests.get(url, headers=headers)
            with requests.get(url, headers=headers) as response:
                response.raise_for_status()
                data = response.json()

            # Extract the primary document corresponding to the target accession number
            recent_filings = data['filings']['recent']
            index = recent_filings['accessionNumber'].index(accession_number)
            primary_document = recent_filings['primaryDocument'][index]
            logger.info(f"Primary Document: {primary_document}")

            return primary_document
                     
        except requests.exceptions.JSONDecodeError:
            logger.error("Failed to decode JSON response")
            return []


def file_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True  # File exists
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False  # File does not exist
        else:
            raise e  # Some other error occurred

def dl_s1_filings(headers, s1_filings_bucket, each_s1):
    """ 
    Download and persist S1 filings in S3 as HTML
    """  
    try:
        primary_document = fetch_s1_primary_document(headers, each_s1['cik'], each_s1['accession_number'])
        url = f"https://www.sec.gov/Archives/edgar/data/{each_s1['cik']}/{each_s1['accession_number'].replace('-', '')}/{primary_document}"

        with requests.get(url, headers=headers, stream=True) as response:
            response.raise_for_status()
            html_content = response.text
        
        sanitized_form_type = each_s1['form_type'].replace('/', '')
        s3_file_path = f"{each_s1['company_name']}_{each_s1['cik']}/{sanitized_form_type}_{each_s1['published_datetime']}.html"
        if not file_exists(s1_filings_bucket, s3_file_path):
            s3.upload_fileobj(BytesIO(html_content.encode('utf-8')), s1_filings_bucket, s3_file_path)
            logger.info(f"The HTML document has been uploaded to S3 bucket {s1_filings_bucket} as {s3_file_path}.")
            
            # Confirm the file has been uploaded successfully
            if file_exists(s1_filings_bucket, s3_file_path):
                logger.info(f"Confirmed that {s3_file_path} exists in S3.")
                return s3_file_path
            else:
                logger.error(f"Failed to confirm the upload of {s3_file_path} to S3.")
                return None
                
        
        else:
            logger.info(f"File {s3_file_path} already exists, skipping upload.")
            return None

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")  # Log specific HTTP errors
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request failed: {req_err}")  # Catch all request-related errors
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    return None

def send_to_sqs(queue_url, message_body):
    sqs = boto3.client('sqs')
    try:
        response = sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
        logger.info(f"Message sent to SQS with message ID: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Failed to send message to SQS: {e}")
        raise e

def handler(event, context):
    s1_filings_bucket = os.environ['S1_FILINGS_HTML_BUCKET']
    queue_url = os.environ['S1_QUEUE_URL']
    headers = {'User-Agent': 'Your Name or Company Name, your-email@example.com'}
    s1_filings = fetch_s1_rss(headers)
    
    logger.info(f"s1_filings: {s1_filings}")

    try:
        for each_s1 in s1_filings:      
        
            s3_file_path = dl_s1_filings(headers, s1_filings_bucket, each_s1)

            # If files were successfully saved
            if s3_file_path:
                each_s1['s3_file_path']= s3_file_path
                payload = {
                    's1_filing': each_s1
                }
                send_to_sqs(queue_url, payload)
            else:
                logger.info("No new file was uploaded. Skipping SQS message.")

    except Exception as e:
        logger.error(f"An error occurred in the handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error processing the request: {e}")
        }

    return {
        'statusCode': 200,
        'body': json.dumps(f"Successfully processed and sent message to SQS.")
    }

    


        




