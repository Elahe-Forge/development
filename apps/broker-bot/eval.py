# Evaluate broker bot

import os
import time

import pandas as pd
import weave
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.evaluation import (
    CorrectnessEvaluator,
    EvaluationResult,
    FaithfulnessEvaluator,
    GuidelineEvaluator,
    RelevancyEvaluator,
)
from llama_index.core.llms import ChatMessage
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.bedrock import Bedrock
from llama_index.llms.openai import OpenAI

from eval_questions import eval_questions

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def index_data(data_path):

    data = SimpleDirectoryReader(input_dir=data_path).load_data()
    splitter = SentenceSplitter(chunk_size=512)
    index = VectorStoreIndex.from_documents(data, transformations=[splitter])

    return index


def get_chat_engine(chat_mode, llm):
    if chat_mode == "best":
        chat_engine = index.as_chat_engine(chat_mode="best", llm=llm, verbose=False)
    if chat_mode == "context":
        memory = ChatMemoryBuffer.from_defaults(token_limit=1500)

        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=memory,
            system_prompt=(
                "You are a chat bot. Only provide answers based on FAQ's related to Forge Global. Do not use your general knowledge."
            ),
            verbose=False,
        )
    else:
        print(
            f'Error! Chat Mode {chat_mode} not available. Please use either "best" or "context" for chat_mode.'
        )
    return chat_engine


def extract_answer(chat_engine, prompt: str) -> dict:
    response = chat_engine.chat(prompt)
    return response


def generate_prompt_response(llm, prompt, chat_mode="context"):

    chat_engine = get_chat_engine(chat_mode, llm)

    response = extract_answer(chat_engine, prompt)

    return response


if __name__ == "__main__":
    data_path = "./data/"
    index = index_data(data_path)

    # LLMs
    gpt3 = OpenAI(temperature=0, model="gpt-3.5-turbo")  # gpt-3 (davinci)
    gpt4o_mini = OpenAI(temperature=0, model="gpt-4")  # gpt-4o-mini
    llama3 = Bedrock(model="meta.llama3-70b-instruct-v1:0")  # llama3

    llm_list = [
        ("gpt-4o-mini", gpt4o_mini),
        ("meta.llama3-70b-instruct-v1:0", llama3),
    ]

    response_dict = {}

    for question in eval_questions[0]:
        llm_output = {}
        for llm_tuple in llm_list:
            name, model = llm_tuple
            response_vector = generate_prompt_response(
                model, question, chat_mode="context"
            )

            contexts = []
            for source in response_vector.source_nodes:
                contexts.append(source.node.text)

            # Evaluators
            # RelevancyEvaluator
            relevancy_eval_result = RelevancyEvaluator(llm=gpt3).evaluate_response(
                query=question, response=response_vector
            )
            print("===RelevancyEvaluator+==")
            print(f"Pass: {relevancy_eval_result.passing}")
            print(f"Feedback: {relevancy_eval_result.feedback}")

            # FaithfulnessEvaluator
            faithfulness_eval_result = FaithfulnessEvaluator(
                llm=gpt3
            ).evaluate_response(response=response_vector)
            print("===FaithfulnessEvaluator+==")
            print(f"Pass: {faithfulness_eval_result.passing}")
            print(f"Feedback: {faithfulness_eval_result.feedback}")
            # CorrectnessEvaluator - needs a reference (could use other LLM?)
            # AnswerRelevancyEvaluator

            # ContextRelvancyEvaluator

            # GuidelineEvaluator
            GUIDELINES = [
                "The response should fully answer the query.",
                "The response should avoid hallucinating.",
            ]
            guideline = GUIDELINES[0]
            guideline_evaluator_gpt3 = GuidelineEvaluator(
                llm=gpt3, guidelines=guideline
            )
            guideline_eval_result = guideline_evaluator_gpt3.evaluate(
                query=question,
                contexts=contexts,
                response=response_vector.response,
            )

            print("===GuidelineEvaluator===")
            print(f"Guideline: {guideline}")
            print(f"Pass: {guideline_eval_result.passing}")
            print(f"Feedback: {guideline_eval_result.feedback}")

            llm_output[name] = {
                "query": question,
                "response": response_vector.response,
                "context": contexts,
            }
            break
        response_dict[question] = llm_output
        break

    pd.DataFrame.from_dict(response_dict, orient="index").reset_index().rename(
        columns={"index": "question"}
    )


# Bedrock Llama3
# OpenAI
