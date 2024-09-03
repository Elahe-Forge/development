import os

import boto3
import helpers.llmDict as llmDict
from botocore.exceptions import ClientError

# from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


def get_secret(secret_name, region_name):

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e

    secret = get_secret_value_response["SecretString"]

    return secret


OPENAI_API_KEY = get_secret("data-science-and-ml-models/openai", "us-west-2")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


class DocumentReader:

    def __init__(self, model_id, llm_kwargs={"temperature": 0}):
        self.model_id = model_id
        self.source = llmDict.dict[self.model_id]["source"]
        self.chat_llm = llmDict.dict[self.model_id]["chat_llm"]

        if self.model_id not in llmDict.dict:
            models_available = llmDict.dict.keys()
            raise Exception(
                f"Model not available! See list of available models to use: \n {models_available}"
            )

        if self.source == "bedrock":
            # Create a Bedrock Runtime client in the AWS Region you want to use.
            self.bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
            self.llm = ChatBedrock(
                client=self.bedrock, model_id=self.model_id, model_kwargs=llm_kwargs
            )

        elif self.source == "openai":
            self.llm = ChatOpenAI(
                model=self.model_id,
                temperature=0,
            )

        else:
            raise Exception("Only OpenAI and Bedrock models implemented!")

    def run_llm_extract(
        self,
        document: str,
        template: str,
        output_format: str,
        pref_shares_list: list = [],
    ):
        """Extract data from COI"""

        input_dict = {"document": document}
        if output_format != "":
            input_dict["output_format"] = output_format

        if pref_shares_list != []:
            input_dict["preferred_shares_list"] = pref_shares_list

        input = template.format(**input_dict)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant!",
                ),
                ("human", "{input}"),
            ]
        )

        # num_tokens = self.llm.get_num_tokens(input)
        # print(f"{num_tokens} document tokens")
        # print("----------------------------------------")

        input_dict = {"input": input}
        llm_chain = prompt | self.llm

        return llm_chain.invoke(input_dict)
