
"""
Processes messages from the SQS queue. 
Fetches and stores news for each issuer received in the message.
"""

import os
import boto3
import datetime
from botocore.exceptions import ClientError
import logging
import pandas as pd
from bs4 import BeautifulSoup
from langchain.chains import LLMChain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
import io 

import re
import requests
import uuid

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# set the LLM model to use for news analysis
def init_llm():

    # This configuration needs to be parameterized for 
    # deployment to other environments
    secret_name = "data-science-and-ml-models/openai"
    region_name = "us-west-2"
    llm = None

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        llm = ChatOpenAI(model='gpt-3.5-turbo', openai_api_key=secret)
        return llm
    except ClientError as e:
        logger.error(f'Error fetching secret: {e}')
        return None
    except Exception as e:
        logger.error(f'Error initializing llm: {e}') 
        return None

# Get the news from the url and strip out all html returning raw text
#
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

def summarize_news(raw_txt : str, llm) -> str:
    if raw_txt is None:
        return None
    
    human_message_template = """
        Below is the raw text content from a news article about a company. Please provide a short ~50 word summary
        of the contents of the article in the style of a neutral financial analyst.
        
        Please do not use the phrase "As a neutral financial analyst."

        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)
    news_summarized = ''

    try:
        chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])
        chain = LLMChain(llm=llm, prompt=chat_prompt)
        news_summarized = chain.invoke({"content": raw_txt})
        return news_summarized['text']
    except Exception as e:
        logger.error(f'Error summarizing news: {e}')
        return None

def rate_reliability(source : str, raw_txt : str, llm) -> int:
    if raw_txt is None:
        return None
    
    human_message_template = """
        Given the source of an article and its contents, rate the perceived "reliability" of the content on a
        scale of 1-5, where 1 is unreliable and 5 is very reliable. 
        
        Very reliable content would be unbiased from a reliable major source, whereas unreliable content would be
        clearly biased and from low quality sources such as industry press release syndications or similar publications.
        
        Do not return anything other than a number from 1-5.

        source: {source}
        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)

    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    try:
        reliability_str = chain.invoke({"content": raw_txt, "source": source})
        reliability = float(reliability_str['text'])
        return reliability
    except Exception as e:
        logger.error(f'Error rating reliability: {e}')
        return None
    

def rate_sentiment(raw_txt : str, llm) -> str:
    if raw_txt is None:
        return None
    
    human_message_template = """
        Given the text of an article, rate the sentiment of the article from 1-5 with 1 being very negative and 5 being
        very positive. 3 should be neutral.
        
        Do not return any text other than the rating.

        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)

    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    
    try:
        sentiment_str = chain.invoke({"content": raw_txt})
        sentiment = float(sentiment_str['text'])
        return sentiment
    except Exception as e:
        logger.error(f'Error rating sentiment: {e}')
        return None


def rate_relevance(raw_txt : str, llm) -> str:
    if raw_txt is None:
        return None
    
    human_message_template = """
        Given the text of an article, rate the relevance of the article from 1-5 with 1 being irrelevant and 5 being
        very relevant. 3 should be neutral.
        
        Relevance should be judged according to the standards of business news. Business announcements such as partnerships,
        new products, leadership changes, funding, layoffs etc should be considered relevant. News like celebrity
        endorsements or similar should be considered less relevant unless very impactful.
        
        Relevance is also relative to the fact that the news is meant for a syndication about tech startups. If the news
        appears to not be about a tech startup, relevance should be low (less than 3.)
        
        Do not return any text other than the rating.

        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)

    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    try:
        relevance_str = chain.invoke({"content": raw_txt})
        relevance = float(relevance_str['text'])
        return relevance
    except Exception as e:
        logger.error(f'Error rating relevance: {e}')
        return None


def rate_controversy(raw_txt : str, llm) -> str:
    if raw_txt is None:
        return None
    
    human_message_template = """
        Given the text of an article, rate how controversial the article is on a scale of 1-5 with 5 being the
        most controversial, and 1 being the least. Controversial articles (for our purposes) would be articles which 
        would be unsuitable for syndication on a business news site. Controversial articles would include:
        overly political articles, or articles implicating the company in some sort of criminal or civil proceeding.
        News related to criminal activity should be rated 5.
        
        Do not return any text other than the rating.
        
        Do not prefix ratings with any text such as "Rating:

        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)

    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    try:
        controversy_str = chain.invoke({"content": raw_txt})
        controversy = float(controversy_str['text'])
        return controversy
    except Exception as e:
        logger.error(f'Error rating controversy: {e}')
        return None

# Tags - comma separated list of tags
def get_tags(raw_txt : str, llm) -> bool:
    if raw_txt is None:
        return None
    
    human_message_template = """
        Given the text of an article, propose a list of 5-10 tags which might be applicable to the article.
        
        We primarily care about business related tags. Some examples might include:
        
        Valuation
        Stock
        IPO
        S-1
        M&A
        SPAC
        Funding Round
        Unicorn
        
        Feel free to generate other business related tags you deem relevant.
        
        Return a comma separated list of tags, with no other text.

        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)

    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    try:
        tags = chain.invoke({"content": raw_txt})
        return tags['text'] # comma separated list of tags
    except Exception as e:
        logger.error(f'Error getting tags: {e}')
        return None 

# Intent was to make lambda reusable for different source types
# only DynamoDB is supported    
def get_issuer_items(records : dict, source_type : str) -> dict:
    if source_type != 'dynamodb':
        raise Exception(f'source type: {source_type} not supported')

    news_records = []
    for record in records:
        try:
            if record['eventName'] != 'REMOVE':
                sequence_number = record[source_type]['SequenceNumber']
                company_name_link_date = record[source_type]['Keys']['company_name_link_date']['S']
                issuer = record[source_type]['NewImage']['company_name']['S']
                news_date = record[source_type]['Keys']['date']['S']
                news_title = record[source_type]['NewImage']['title']['S']
                news_source = record[source_type]['NewImage']['source']['S']
                news_url = record[source_type]['NewImage']['link']['S']


                news_records.append({'sequence_number':sequence_number,
                                     'company_name_link_date':company_name_link_date,
                                        'issuer':issuer,
                                        'news_date':news_date,
                                        'news_title':news_title,
                                        'news_source':news_source,
                                        'news_url':news_url})
            
        except Exception as e:
            logger.error(f'problem with record: {record}\nerror{e}')
    return news_records


# To persist news analysis to S3 as Parquet
def persist_news_analysis(news_records, s3_bucket):
    s3_client = boto3.client('s3')

    if len(news_records) > 0:
        for record in news_records:
            try:
                issuer_name = record['issuer'].replace(" ", "_").lower()  # Replace spaces with underscores and convert to lowercase
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")  
                unique_id = uuid.uuid4()  # Generate a unique identifier to ensure uniqueness
                
                df = pd.DataFrame([record])
                parquet_buffer = io.BytesIO()
                df.to_parquet(parquet_buffer, index=False)

                s3_object_key = f'news-articles/{issuer_name}/news_record_{timestamp}_{unique_id}.parquet'
                s3_client.put_object(Bucket=s3_bucket, Key=s3_object_key, Body=parquet_buffer.getvalue())
                
                logger.info(f"Persisted record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}' with key '{s3_object_key}'")
            except ClientError as e:
                logger.error(f"Failed to persist record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error occurred while persisting record for issuer '{issuer_name}': {e}")
    else:
        logger.info("No records to persist")

   

def handler(event, context):
    s3_bucket = os.environ['S3_BUCKET']
    llm = init_llm()
    if llm:     
        news_records = get_issuer_items(event['Records'], 'dynamodb')
        for news_record in news_records:
            logger.info(f'Processing news record: {news_record}')
            try:
                raw_news_text = get_raw_news_text(news_record['news_url'])
                if raw_news_text:
                    news_record['summary'] = summarize_news(raw_news_text, llm)
                    news_record['reliability'] = rate_reliability(news_record['news_source'], raw_news_text, llm)
                    news_record['sentiment'] = rate_sentiment(raw_news_text, llm)
                    news_record['relevance'] = rate_relevance(raw_news_text, llm)
                    news_record['controversy'] = rate_controversy(raw_news_text, llm)
                    news_record['tags'] = get_tags(raw_news_text, llm)
                    news_record['raw'] = raw_news_text
            except Exception as e:
                logger.error(f'Error processing news record: {news_record}, error: {e}')    
        persist_news_analysis(news_records, s3_bucket)
        return {'batchItemFailures': []}
    else:
        logger.error('Error initializing llm')
        return {'batchItemFailures': []}

