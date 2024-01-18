
"""
Processes messages from the SQS queue. 
Fetches and stores news for each issuer received in the message.
"""

import os
import boto3
import json
import datetime
from botocore.exceptions import ClientError
import logging

from bs4 import BeautifulSoup

from langchain import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chat_models import ChatOpenAI

import re
import requests

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
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    try:
        secret = get_secret_value_response['SecretString']
        # TODO this code can be parameterized for the model used
        llm = ChatOpenAI(model='gpt-4', openai_api_key=secret)
        return llm
    except Exception as e:
        logger.error(f'Error initializing llm: {e}') 
        return llm

# Get the news from the url and strip out all html returning raw text
#
def get_raw_news_text(url : str) -> str: # throws http error if problems w/request
   # Send a GET request to the URL
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

def summarize_news(raw_txt : str, llm) -> str:
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
        news_summarized = chain.run(content=raw_txt)

    except Exception as e:
        logger.error(f'error with summarize news{e}')
        raise Exception(f"error with summarize news, {e}")
    
    return news_summarized

def rate_reliability(source : str, raw_txt : str, llm) -> int:
    human_message_template = """
        Given the source of an article and its contents, rate the perceived "reliability" of the content on a
        scale of 1.0-5.0, where 1 is unreliable and 5 is very reliable. 
        
        Very reliable content would be unbiased from a reliable major source, whereas unreliable content would be
        clearly biased and from low quality sources such as industry press release syndications or similar publications.
        
        Do not return anything other than a number from 1-5.

        source: {source}
        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)

    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    reliability_str = chain.run(content=raw_txt, source=source)

    try:
        reliability = int(reliability_str)
        return reliability
    except:
        return None
    
# Sentiment - float? for now, returns 1.0-5.0
# 
def rate_sentiment(raw_txt : str, llm) -> str:
    human_message_template = """
        Given the text of an article, rate the sentiment of the article from 1.0-5.0 with 1 being very negative and 5 being
        very positive. 3 should be neutral.
        
        Do not return any text other than the rating.

        {content}
    """

    human_message_prompt = HumanMessagePromptTemplate.from_template(human_message_template)

    chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    sentiment_str = chain.run(content=raw_txt)

    try:
        sentiment = float(sentiment_str)
        return sentiment
    except:
        return None

# Relevance - float? for now, returns 1.0-5.0
def rate_relevance(raw_txt : str, llm) -> str:
    human_message_template = """
        Given the text of an article, rate the relevance of the article from 1.0-5.0 with 1 being irrelevant and 5 being
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

    relevance_str = chain.run(content=raw_txt)

    try:
        relevance = float(relevance_str)
        return relevance
    except:
        return None

# Controversy - float? for now, returns 1.0-5.0
def rate_controversy(raw_txt : str, llm) -> str:
    human_message_template = """
        Given the text of an article, rate how controversial the article is on a scale of 1.0-5.0 with 5 being the
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
        controversy_str = chain.run(content=raw_txt)
        controversy = float(controversy_str)
        return controversy
    except:
        return None

# Tags - comma separated list of tags
def get_tags(raw_txt : str, llm) -> bool:
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
        tags = chain.run(content=raw_txt)
        return tags # comma separated list of tags
    except:
        return None  

# Intent was to make lambda reusable for different source types
# only DynamoDB is supported    
def get_issuer_items(records : dict, source_type : str) -> dict:
    if (source_type == 'dynamodb'):
        news_attributes = []
        for record in records:
            try:
                if record['eventName'] != 'REMOVE':
                    sequence_number = record[source_type]['SequenceNumber']
                    issuer = record[source_type]['Keys']['company_name']['S']
                    news_date = record[source_type]['NewImage']['date']['S']
                    news_title = record[source_type]['NewImage']['title']['S']
                    news_source = record[source_type]['NewImage']['source']['S']
                    news_url = record[source_type]['NewImage']['link']['S']

                    news_attributes.append({'sequence_number':sequence_number,
                                            'issuer':issuer,
                                            'news_date':news_date,
                                            'news_title':news_title,
                                            'news_source':news_source,
                                            'news_url':news_url})
                else:
                    # no action required for deleted records
                    pass
            except Exception as e:
                logger.error(f'problem with record: {record}\nerror{e}')
        return news_attributes
    else:
        raise Exception(f'source type: {source_type} not supported')
    
# def news_analysis(llm:)
def handler(event, context):
    llm = init_llm()
    if llm:     
        for record in get_issuer_items(event['Records'], 'dynamodb'): 
            
            logger.info(f'issuer = {record["issuer"]}, news_date = {record["news_date"]}, \
                            news_title = {record["news_title"]}, news_source = {record["news_source"]}, \
                            news_url ={record["news_url"]}')
            
            try:
                raw_news_text = get_raw_news_text(record['news_url'])
                try:
                    record['summary'] = summarize_news(raw_news_text, llm)
                    record['reliability'] = rate_reliability(record['news_source'], raw_news_text, llm)
                    record['sentiment'] = rate_sentiment(raw_news_text, llm)
                    record['relevance'] = rate_relevance(raw_news_text, llm)
                    record['controversy'] = rate_controversy(raw_news_text, llm)
                    record['tags'] = get_tags(raw_news_text, llm)      

                except Exception as e:
                    logger.error(f'News analysis error for record:{record}')
                    continue
            except Exception as e:
                # not stopping on http errors (some just won't work w/this configuration - see phase 2 for possible fixes)
                logger.error(f'Error getting link: {record["news_url"]}, for record:{record}') 
                continue          
        
        return {'batchItemFailures': []}
        
    else:
        logger.error(f'Error initializing llm')
        return {'batchItemFailures': []}