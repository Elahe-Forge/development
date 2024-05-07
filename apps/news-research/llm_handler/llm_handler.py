import boto3
import json
import re
import logging
from botocore.exceptions import ClientError
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_prompt_by_metric(metric_name, content, source=None):
    if content is None:
        return None

    prompts = {
        "summary": f"""
            Below is the raw text content from a news article about a company. Please provide a short ~50 word summary
            of the contents of the article in the style of a neutral financial analyst.
            
            Do not return any text other than the summary."
            
            {content}
        """,
        "reliability": f"""
            Given the source of an article and its contents, rate the perceived "reliability" of the content on a
            scale of 1-5, where 1 is unreliable and 5 is very reliable.
            
            Very reliable content would be unbiased from a reliable major source, whereas unreliable content would be
            clearly biased and from low quality sources such as industry press release syndications or similar publications.
            
            Do not return anything other than a number from 1-5.
            
            source: {source}
            {content}
        """,
        "sentiment": f"""
            Given the text of an article, rate the sentiment of the article from 1-5 with 1 being very negative and 5 being
            very positive. 3 should be neutral.
            
            Do not return any text other than the rating.
            
            {content}
        """,
        "relevance": f"""
            Given the text of an article, rate the relevance of the article from 1-5 with 1 being irrelevant and 5 being
            very relevant. 3 should be neutral.
            
            Relevance should be judged according to the standards of business news. Business announcements such as partnerships,
            new products, leadership changes, funding, layoffs etc should be considered relevant. News like celebrity
            endorsements or similar should be considered less relevant unless very impactful.
            
            Relevance is also relative to the fact that the news is meant for a syndication about tech startups. If the news
            appears to not be about a tech startup, relevance should be low (less than 3.)
            
            Do not return any text other than the rating.
            
            {content}
        """,
        "controversy": f"""
            Given the text of an article, rate how controversial the article is on a scale of 1-5 with 5 being the
            most controversial, and 1 being the least. Controversial articles (for our purposes) would be articles which 
            would be unsuitable for syndication on a business news site. Controversial articles would include:
            overly political articles, or articles implicating the company in some sort of criminal or civil proceeding.
            News related to criminal activity should be rated 5.
            
            Do not return any text other than the rating.
            
            {content}
        """,
        "tags": f"""
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
            
            Return a comma separated list of tags.

            Do not return any text other than the tags.
            
            {content}
        """
    }

    return prompts.get(metric_name, "Invalid metric name")


class ClaudeProcessor:
    def __init__(self, model_handle):
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-west-2')
        self.model_id = model_handle
        self.accept = 'application/json'
        self.content_type = 'application/json'
        self.base_body = {
            "max_tokens_to_sample": 2000,
            "temperature": 0.1,
            "top_p": 0.9,
        }

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
            prompt = get_prompt_by_metric(metric_name, content, source)
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
                    return match.group()
                return completion  # Handle non-numerical completion gracefully 
            elif metric_name in ["summary", "tags"]:
                # Attempt to clean up the completion
                return self.clean_phrase(completion)
            else:
                return None
        except Exception as e:
            logger.error(f"Error processing {metric_name} with Claude on Bedrock: {e}")
            return None



class GPTProcessor:
    def __init__(self, model_handle):
        self.llm = self.init_gpt_llm(model_handle)

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

        prompt = get_prompt_by_metric(metric_name, content, source)
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


