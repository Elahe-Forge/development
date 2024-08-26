
"""

"""

import os
import boto3
import logging
import requests
import feedparser
import re
import pdfkit
from io import BytesIO
from weasyprint import HTML


# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def fetch_s1_rss(headers):
    rss_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=S-1&output=atom" 
    
    try:
        response = requests.get(rss_url, headers=headers, verify=False)
        logger.info(f"response.status_code: {response.status_code}")
   
        feed = feedparser.parse(response.content)
        s1_filings = []

        for entry in feed.entries:
            if 'S-1' in entry.title or 'S-1/A' in entry.title:
                s1_filings.append({
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.summary,
                    'published': entry.updated,
                    'id': entry.id
                })
        
        return s1_filings

    except Exception as e:
        # Log any exception that occurs during invocation
        logger.error(f"Failed to fetch RSS feed: {e}")
        return []


def fetch_accession_cik_company_name(s1_filing):   
    
    try:
        accession_number = None
        cik = None
        company_name = None

        accession_pattern = r"accession-number=(\d{10}-\d{2}-\d{6})"
        accession_match = re.search(accession_pattern, s1_filing.get('id', ''))

        if accession_match:
            accession_number = accession_match.group(1)
            logger.info(f"Accession Number: {accession_number}")
        else:
            logger.error("No match found for accession number.")

        cik_pattern = r"\((\d{10})\)"
        cik_match = re.search(cik_pattern, s1_filing.get('title', ''))

        if cik_match:
            cik = cik_match.group(1)
            logger.info(f"CIK: {cik}")
        else:
            logger.error("No match found for CIK.")

        company_name_pattern = r"- (.*?) \("
        company_name_match = re.search(company_name_pattern, s1_filing.get('title', ''))

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


def dl_s1_filings(headers, url, s1_filings_bucket, company_name, date_time):
    """ 
    Download and persist S1 filings in S3 as HTML and PDF
    """  
    try:
        s3 = boto3.client('s3')
        response = requests.get(url, headers=headers, stream=True)
        html_content = response.text

        # Define S3 paths (S3 'folders' are just prefixes in the key name)
        s3_html_path = f"{company_name}/{date_time}.html"
        s3_pdf_path = f"{company_name}/{date_time}.pdf"

        # Upload HTML content directly to S3
        s3.upload_fileobj(BytesIO(html_content.encode('utf-8')), s1_filings_bucket, s3_html_path)
        logger.info(f"The HTML document has been uploaded to S3 bucket {s1_filings_bucket} as {s3_html_path}.")

        # # Convert HTML content to PDF
        # pdf_stream = BytesIO()
        # pdfkit.from_string(html_content, output_path=pdf_stream)  # Convert to PDF and save in BytesIO stream
        # pdf_stream.seek(0)  # Reset the stream position to the beginning
        # Generate PDF from HTML content
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)

        # Upload PDF directly to S3
        s3.upload_fileobj(pdf_file, s1_filings_bucket, s3_pdf_path)
        logger.info(f"The PDF document has been uploaded to S3 bucket {s1_filings_bucket} as {s3_pdf_path}.")

        # # Optionally close the streams
        # pdf_stream.close()

    except requests.exceptions.JSONDecodeError:
        logger.error(f"Failed to retrieve the document. Status code: {response.status_code}")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

def handler(event, context):
    s1_filings_bucket = os.environ['S1_FILINGS_BUCKET']
    headers = {'User-Agent': 'Your Name or Company Name, your-email@example.com'}
    s1_filings = fetch_s1_rss(headers)
    
    logger.info(f"s1_filings: {s1_filings}")
    
    for each_s1 in s1_filings:
        accession_number, cik, company_name = fetch_accession_cik_company_name(each_s1)       
        primary_document = fetch_s1_primary_document(headers, cik, accession_number)
        
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{primary_document}"
        dl_s1_filings(headers, url, s1_filings_bucket, company_name, each_s1['published'])

    return {
        'statusCode': 200,
        'body': f'PDFs saved to S3'
    }

    


        




