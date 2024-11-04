import boto3
import json
import re
import logging
from botocore.exceptions import ClientError
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
import boto3
import json
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def load_prompts_from_s3(version, s3_news_prompts_bucket):
    """
    Access prompt json file from S3 bucket
    """
    s3 = boto3.client('s3')
    file_key = f'{version}/prompts.json'

    try:
        response = s3.get_object(Bucket=s3_news_prompts_bucket, Key=file_key)
        prompts = json.loads(response['Body'].read())
        return prompts
    except ClientError as e:
        logger.error(f'Error fetching prompts from S3: {e}')
        return {}
    except Exception as e:
        logger.error(f'Error loading prompts: {e}')
        return {}

def get_prompt_by_metric(metric_name, content, source, version, s3_news_prompts_bucket):
    if content is None:
        return None

    prompts = load_prompts_from_s3(version, s3_news_prompts_bucket)

    prompt_template = prompts.get(metric_name, "")
    prompt = prompt_template.format(content=content, source=source if source else "")
    
    return prompt


class ClaudeProcessor:
    def __init__(self, model_handle, s3_news_prompts_bucket, prompt_version):
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-west-2')
        self.model_id = model_handle
        self.accept = 'application/json'
        self.content_type = 'application/json'
        self.base_body = {
            "max_tokens_to_sample": 2000,
            "temperature": 0.1,
            "top_p": 0.9,
        }
        self.s3_news_prompts_bucket = s3_news_prompts_bucket
        self.version = prompt_version

    def clean_phrase(self, text):
        """
        To clean up the summary and tags that Claude provides
        Example: 
            "Here is a \d+ word summary of the article in the style of a neutral financial analyst:"
            "Here are \d+ suggested tags for the article:"
        """    
        # Pattern to start with 'Here is' or 'Here are' and end with the first ':' followed by any whitespace
        pattern = r"Here (is|are).*?:\s*"
        
        # Using the DOTALL flag to match across multiple lines
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
        
        return cleaned_text

    def process_metric(self, metric_name, content, source=None):
        """
        Process content based on the metric using Claude model on AWS Bedrock.
        Returns:
            float or str or None: The processed score or text from the model, or None on failure.
        """
        if content is None:
            return None

        try:
            prompt = get_prompt_by_metric(metric_name, content, source, self.version, self.s3_news_prompts_bucket)
            self.base_body["prompt"] = f"\n\nHuman:{prompt}\nraw text:{prompt}\n\nAssistant:"

            body = json.dumps(self.base_body)
            response = self.bedrock.invoke_model(body=body, modelId=self.model_id, accept=self.accept, contentType=self.content_type)
            response_body = json.loads(response.get('body').read())
            completion = response_body.get('completion')

            # Process the completion based on the metric
            if metric_name in ["reliability", "sentiment", "relevance", "controversy"]:
                # Attempt to extract a number in the completion
                match = re.search(r'\d+', completion)
                if match:
                    match_value = int(match.group())
                    if 1 <= match_value <= 5:
                        return match_value
                    else:
                        return 1
                return 1
            elif metric_name == "summary":
                return self.clean_phrase(completion)
            elif metric_name == "tags":
                cleaned_phrase = self.clean_phrase(completion)   
                if isinstance(cleaned_phrase, str):
                    return [tag.strip() for tag in cleaned_phrase.split(",")]
            else:
                return None
        except Exception as e:
            logger.error(f"Error processing {metric_name} with Claude on Bedrock: {e}")
            return None



class GPTProcessor:
    def __init__(self, model_handle, s3_news_prompts_bucket, prompt_version):
        self.llm = self.init_gpt_llm(model_handle)
        self.s3_news_prompts_bucket = s3_news_prompts_bucket
        self.version = prompt_version

    def init_gpt_llm(self, model_handle):
        secret_name = "data-science-and-ml-models/openai"
        region_name = "us-west-2"

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager', region_name=region_name)

        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
            secret = get_secret_value_response['SecretString']
            return ChatOpenAI(model=model_handle, openai_api_key=secret)
        except ClientError as e:
            logger.error(f'Error fetching secret: {e}')
            return None
        except Exception as e:
            logger.error(f'Error initializing GPT model: {e}')
            return None

    def process_metric(self, metric_name, content, source=None):
        if content is None or self.llm is None:
            return None

        prompt = get_prompt_by_metric(metric_name, content, source, self.version, self.s3_news_prompts_bucket)
        human_message_prompt = HumanMessagePromptTemplate.from_template(prompt)
        chat_prompt = ChatPromptTemplate.from_messages([human_message_prompt])
        chain = LLMChain(llm=self.llm, prompt=chat_prompt)

        try:
            if metric_name == "reliability":
                # If a source is required, pass it along with the content
                response = chain.invoke({"content": content, "source": source})
                return float(response['text'])
            else:
                response = chain.invoke({"content": content})
                if metric_name in ["summary", "sentiment", "relevance", "controversy", "tags"]:
                    return response['text']
                return None
        except Exception as e:
            logger.error(f'Error processing {metric_name}: {e}')
            return None


