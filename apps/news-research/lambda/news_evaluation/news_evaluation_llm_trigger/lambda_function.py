"""
Evaluates textual summaries using specific metrics, 
interacts with the AWS Bedrock model to obtain evaluation scores, 
and persists these scores along with additional metadata to an AWS S3 bucket.

"""

import os
import json
import boto3
import logging
import datetime
import pandas as pd
from botocore.exceptions import ClientError
import io
import re
import uuid


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def create_evaluation_prompt(metric_name: str, document: str, summary: str) -> str:
    # Evaluation prompt template 
    EVALUATION_PROMPT_TEMPLATE = """
    You will be given one summary written for an article. Your task is to rate the summary on one metric.
    Your answer should only be an integer score between 1-5. Do not provide any explanation and text.
    Please make sure you read and understand these instructions very carefully. 
    Please keep this document open while reviewing, and refer to it as needed.

    Evaluation Criteria:

    {criteria}

    Evaluation Steps:

    {steps}

    Example:

    Source Text:

    {document}

    Summary:

    {summary}

    Evaluation Form (scores ONLY):

    - {metric_name}
    """

    # Metric-specific criteria and steps
    metrics = {
        "Relevance": {
            "criteria": """
            Relevance(1-5) - selection of important content from the source. The summary should include only important information from the source document. Annotators were instructed to penalize summaries which contained redundancies and excess information.
            """,
            "steps": """
            1. Read the summary and the source document carefully.
            2. Compare the summary to the source document and identify the main points of the article.
            3. Assess how well the summary covers the main points of the article, and how much irrelevant or redundant information it contains.
            4. Assign only a relevance score integer from 1 to 5.
            """
        },
        "Coherence": {
            "criteria": """
            Coherence(1-5) - the collective quality of all sentences. We align this dimension with the DUC quality question of structure and coherence whereby "the summary should be well-structured and well-organized. The summary should not just be a heap of related information, but should build from sentence to a coherent body of information about a topic."
            """,
            "steps": """
            1. Read the article carefully and identify the main topic and key points.
            2. Read the summary and compare it to the article. Check if the summary covers the main topic and key points of the article, and if it presents them in a clear and logical order.
            3. Assign only an integer score for coherence on a scale of 1 to 5, where 1 is the lowest and 5 is the highest based on the Evaluation Criteria.
            """
        },
        "Consistency": {
            "criteria": """
            Consistency(1-5) - the factual alignment between the summary and the summarized source. A factually consistent summary contains only statements that are entailed by the source document. Annotators were also asked to penalize summaries that contained hallucinated facts.
            """,
            "steps": """
            1. Read the article carefully and identify the main facts and details it presents.
            2. Read the summary and compare it to the article. Check if the summary contains any factual errors that are not supported by the article.
            3. Assign only an integer score for consistency based on the Evaluation Criteria.
            """
        },
        "Fluency": {
            "criteria": """
            Fluency(1-5): the quality of the summary in terms of grammar, spelling, punctuation, word choice, and sentence structure.
            1: Very Poor. The summary is almost unintelligible due to numerous grammatical and spelling errors.
            2: Poor. The summary has many errors that make it hard to understand or sound unnatural.
            3: Fair. The summary has some errors that affect the clarity or smoothness of the text, but the main points are still comprehensible.
            4: Good. The summary has few errors and is easy to read and follow.
            5: Very Good. The summary is excellently written with no grammatical or spelling errors, offering a smooth and professional reading experience.
            """,
            "steps": """
            Read the summary and evaluate its fluency based on the given criteria. 
            Assign only an integer score for fluency from 1 to 5.
            """
        }
    }

    # Select the appropriate criteria and steps based on the metric name
    if metric_name in metrics:
        criteria = metrics[metric_name]["criteria"]
        steps = metrics[metric_name]["steps"]
    else:
        raise ValueError("Invalid metric name provided.")

    # Format the prompt with the selected criteria, steps, and other details
    return EVALUATION_PROMPT_TEMPLATE.format(
        criteria=criteria,
        steps=steps,
        metric_name=metric_name,
        document=document,
        summary=summary
    )



def get_eval_score_claude(document: str, summary: str, metric_name: str):
    try:
        bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-west-2')
        
        prompt = create_evaluation_prompt(metric_name, document, summary)

        body = json.dumps({
            "prompt": f"\n\nHuman:{prompt}\nraw text:{prompt}\n\nAssistant: I only provide an integer score between 1-5.",
            "max_tokens_to_sample": 2000,
            "temperature": 0.1,
            "top_p": 0.9,})


        modelId = 'anthropic.claude-v2'
        accept = 'application/json'
        contentType = 'application/json'

        response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)    
        response_body = json.loads(response.get('body').read())
        completion = response_body.get('completion')
        
        # Attempt to find a number in the completion
        match = re.search(r'\d+', completion)
        if match:
            score = match.group()
        else:
            # Sometimes Claude does not listen to the prompt to return a number
            score = completion


        return score
    except Exception as e:
        print(e)
        return None


def store_news(s3_bucket, news_record, news_metrics):
    s3_client = boto3.client('s3')
    if len(news_metrics) > 0:
        results = {}
        try:
            issuer_name = news_record['issuer'].replace(" ", "_").lower()  # Replace spaces with underscores and convert to lowercase
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f") 
            unique_id = uuid.uuid4()  # Generate a unique identifier to ensure uniqueness 
            company_name_link_date = news_record['company_name_link_date']
            
            results["issuer"] = issuer_name
            results["sequence_number"] = news_record['sequence_number']
            results["company_name_link_date"] = company_name_link_date

            results.update(news_metrics)
            logger.info(f"Evaluation results {results}")


            df = pd.DataFrame([results])
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False)

            s3_object_key = f'news-evaluation/{issuer_name}/llm_evaluation_{timestamp}_{unique_id}.parquet'
            s3_client.put_object(Bucket=s3_bucket, Key=s3_object_key, Body=parquet_buffer.getvalue())
            
            logger.info(f"Persisted evaluation record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}' with key '{s3_object_key}'")
        except ClientError as e:
            logger.error(f"Failed to persist evaluation record for issuer '{issuer_name}' to S3 bucket '{s3_bucket}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error occurred while persisting evaluation record for issuer '{issuer_name}': {e}")
    else:
        logger.info("No evaluation records to persist")
        



def handler(event, context):

    s3_bucket = os.environ.get("S3_BUCKET")

    # Get the message from the SQS event
    for record in event['Records']:
        try:
            message_body = json.loads(record['body']) # body is the actual content of the message that is enqueued in the parent Lambda function
            for news_record in message_body: 
                if news_record['raw']:
                    company_name = news_record['issuer']  
                    logger.info(f"Processing news record for {company_name}")

                    scores_dict = {}
                    for metric_name in ["Relevance", "Coherence", "Consistency", "Fluency"]:
                        eval_score = get_eval_score_claude(news_record['raw'], news_record['summary'], metric_name)
                        scores_dict[metric_name] = eval_score
                        logger.info(f"Metric: {metric_name}, Score: {eval_score}")
                        
                    store_news(s3_bucket, news_record, scores_dict)
        


        except Exception as e:
            logger.error(f"Error : {str(e)}")
            raise e

    return {
        'statusCode': 200,
        'body': json.dumps('Triggered ')
    }
