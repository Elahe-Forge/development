import os
import time
from pathlib import Path
from typing import Dict, List

import boto3
import streamlit as st
from llama_index.core import (
    PromptTemplate,
    SQLDatabase,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.llms import ChatResponse
from llama_index.core.objects import ObjectIndex, SQLTableNodeMapping, SQLTableSchema
from llama_index.core.prompts.default_prompts import DEFAULT_TEXT_TO_SQL_PROMPT
from llama_index.core.query_pipeline import FnComponent, InputComponent
from llama_index.core.query_pipeline import QueryPipeline as QP
from llama_index.core.retrievers import SQLRetriever
from llama_index.core.schema import TextNode
from llama_index.llms.bedrock import Bedrock
from llama_index.llms.openai import OpenAI
from llama_index.readers.athena import AthenaReader
from sqlalchemy import text

os.environ["OPENAI_API_KEY"] = "YOUR KEY HERE"
AWS_REGION = "us-west-2"
SCHEMA_NAME = "datalake-curated-production"
S3_STAGING_DIR = "s3://athena-output-brandtbo-prod/"
WORKGROUP = "primary"

# Dropdown select for LLM to use
option = st.selectbox(
    "Select which LLM to use", ("GPT 3.5 Turbo", "GPT 4", "Claude Instant v1")
)
# Button to Clear Chat
if st.button("Clear Chat"):
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ask me a question about the Forge ICMS Data!",
        }
    ]

# LLMs to use and test
bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
llm_claude_v1 = Bedrock(client=bedrock, model="anthropic.claude-instant-v1")
llm_gpt35 = OpenAI(model="gpt-3.5-turbo", temperature=0)
llm_gpt4 = OpenAI(model="gpt-4", temperature=0)

llm_dictionary = {
    "GPT 3.5 Turbo": llm_gpt35,
    "GPT 4": llm_gpt4,
    "Claude Instant v1": llm_claude_v1,
}
llm_to_use = llm_dictionary[option]


st.header("Forge Chat POC", divider="rainbow")  # Add Chat header

if "messages" not in st.session_state.keys():  # Initialize the chat message history
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ask me a question about the Forge ICMS Data!",
        }
    ]

athena = AthenaReader()
engine = athena.create_athena_engine(
    aws_region=AWS_REGION,
    s3_staging_dir=S3_STAGING_DIR,
    database=SCHEMA_NAME,
    workgroup=WORKGROUP,
)

# Takes 5-10 minutes to index tables upon first load
table_list = [
    "icms_issuer",
    "secondary_transactions",
    "funding_rounds",
    "public_marks",
    "ioi_history",
    "forge_prices",
    "vwap",
    "icms_issuer_ipo_event",
]

table_description = [
    "General information on each issuer, such as sector, sub sector, location, etc. Primary key: slug.",
    "Trade information for each issuer or company, involving the buying and selling of the company's shares. Foreign key: issuer_id_name",
    "Funding round information for each issuer or company. For instance, the Series Seed, Series A, Series B funding round information. Foreign key: issuer_id_name",
    "Public marks information for each issuer or company. Public marks is the value assigned to issuers by mutual funds. These “marks,” which represent the price expressions of some of the largest, most well-informed institutional investors, are emerging as an additional metric that can be used by other investors to more accurately value their private holdings. Foreign key: issuer_id_name",
    "Indication of Interest (IOI) for each issuer or company. An indication of interest is an underwriting expression showing a conditional, non-binding interest in buying a security of the issuer. Foreign key: issuer_id_name",
    "Share price for each issuer or company based on Forge's methodology. Foreign key: issuer_slug",
    "Volume-weighted average price (vwap) for each issuer or company. The table contains various prices across different timespans. vwap_7 is the 7 day volume-weighted average price, vwap_30 is the 30 day volume-weighted average price, etc. Foreign key: issuer_slug",
    "Initial Public Offering (IPO) events for an issuer or company. Foreign key: issuer_slug",
]

sql_database = SQLDatabase(engine, include_tables=table_list)

table_node_mapping = SQLTableNodeMapping(sql_database)
table_schema_objs = [
    SQLTableSchema(table_name=table, context_str=table_description[idx])
    for idx, table in enumerate(table_list)
]

obj_index = ObjectIndex.from_objects(
    table_schema_objs,
    table_node_mapping,
    VectorStoreIndex,
)

obj_retriever = obj_index.as_retriever(similarity_top_k=3)


@st.cache_resource(show_spinner=False)
def index_all_tables(
    _sql_database: SQLDatabase, table_index_dir: str = "table_index_dir"
) -> Dict[str, VectorStoreIndex]:
    with st.spinner(
        text="Loading and indexing the Forge ICMS Data – hang tight! This should take 5-10 minutes."
    ):
        # Index all tables
        if not Path(table_index_dir).exists():
            os.makedirs(table_index_dir)

        vector_index_dict = {}
        engine = _sql_database.engine
        for table_name in _sql_database.get_usable_table_names():
            start_time = time.time()
            print(f"Indexing rows in table: {table_name}")
            if not os.path.exists(f"{table_index_dir}/{table_name}"):
                # get all rows from table
                with engine.connect() as conn:
                    # Customized Queries for specific tables to improve data quality
                    if table_name == "forge_prices":
                        query_str = f"""SELECT * from forge_prices limit 500"""
                    elif table_name == "vwap":
                        query_str = f"""SELECT * from vwap limit 500"""
                    elif table_name == "funding_rounds":
                        query_str = f"""SELECT fr.*, ii.sector, ii.sub_sector 
                                    FROM funding_rounds fr
                                    join icms_issuer ii
                                    on fr.issuer_id_name = ii.slug"""
                    elif table_name == "public_marks":
                        query_str = f"""SELECT pm.*, ii.sector, ii.sub_sector 
                                    FROM public_marks pm
                                    join icms_issuer ii
                                    on pm.issuer_id_name = ii.slug"""
                    elif table_name == "secondary_transactions":
                        query_str = f"""SELECT st.*, ii.sector, ii.sub_sector 
                                    FROM secondary_transactions st
                                    join icms_issuer ii
                                    on st.issuer_id_name = ii.slug"""
                    elif table_name == "ioi_history":
                        query_str = f"""SELECT ih.*, ii.sector, ii.sub_sector 
                                    FROM ioi_history ih
                                    join icms_issuer ii
                                    on ih.issuer_id_name = ii.slug"""
                    elif table_name == "icms_issuer_ipo_event":
                        query_str = f"""SELECT ie.*, ii.sector, ii.sub_sector 
                                    FROM icms_issuer_ipo_event ie
                                    join icms_issuer ii
                                    on ie.issuer_slug = ii.slug"""
                    else:
                        query_str = f'SELECT * FROM "{table_name}"'

                    cursor = conn.execute(text(query_str))
                    result = cursor.fetchall()
                    row_tups = []
                    for row in result:
                        row_tups.append(tuple(row))

                # index each row, put into vector store index
                nodes = [TextNode(text=str(t)) for t in row_tups]

                # put into vector store index (use OpenAIEmbeddings by default)
                index = VectorStoreIndex(nodes)

                # save index
                index.set_index_id("vector_index")
                index.storage_context.persist(f"{table_index_dir}/{table_name}")
            else:
                # rebuild storage context
                storage_context = StorageContext.from_defaults(
                    persist_dir=f"{table_index_dir}/{table_name}"
                )
                # load index
                index = load_index_from_storage(
                    storage_context, index_id="vector_index"
                )
            end_time = time.time()
            print("Time:", (end_time - start_time) / 60)

            vector_index_dict[table_name] = index

        return vector_index_dict


vector_index_dict = index_all_tables(sql_database)

sql_retriever = SQLRetriever(sql_database)


def get_table_context_and_rows_str(
    query_str: str, table_schema_objs: List[SQLTableSchema]
):
    """Get table context string."""
    context_strs = []
    for table_schema_obj in table_schema_objs:
        # first append table info + additional context
        table_info = sql_database.get_single_table_info(table_schema_obj.table_name)
        if table_schema_obj.context_str:
            table_opt_context = " The table description is: "
            table_opt_context += table_schema_obj.context_str
            table_info += table_opt_context

        # also lookup vector index to return relevant table rows
        vector_retriever = vector_index_dict[table_schema_obj.table_name].as_retriever(
            similarity_top_k=10
        )
        relevant_nodes = vector_retriever.retrieve(query_str)
        if len(relevant_nodes) > 0:
            table_row_context = "\nHere are some relevant example rows (values in the same order as columns above)\n"
            for node in relevant_nodes:
                table_row_context += str(node.get_content()) + "\n"
            table_info += table_row_context

        context_strs.append(table_info)
    return "\n\n".join(context_strs)


table_parser_component = FnComponent(fn=get_table_context_and_rows_str)


def parse_response_to_sql(response: ChatResponse) -> str:
    """Parse response to SQL."""
    response = response.message.content
    sql_query_start = response.find("SQLQuery:")
    if sql_query_start != -1:
        response = response[sql_query_start:]
        # TODO: move to removeprefix after Python 3.9+
        if response.startswith("SQLQuery:"):
            response = response[len("SQLQuery:") :]
    sql_result_start = response.find("SQLResult:")
    if sql_result_start != -1:
        response = response[:sql_result_start]
    return response.strip().strip("```").strip()


sql_parser_component = FnComponent(fn=parse_response_to_sql)

# text2sql_prompt = DEFAULT_TEXT_TO_SQL_PROMPT.partial_format(dialect=engine.dialect.name)

text2sql_prompt_str = """Given an input question, fully understand the questionso you can first create a syntactically correct Amazon Athena query to run, then look at the results of the query and return the answer.

Never query for all the columns from a specific table, only ask for a few relevant columns given the question. DO NOT USE DATE_SUB! This will throw an error. Do not make up columns. User your table knowledge to select the best columns to answer the question.

When querying for date specific items DO NOT USE DATE_SUB! This will throw an error. Use this syntax instead: 
- date("2021-01-01")
- to get current date use CURRENT_DATE(date). For example to get current year use YEAR(CURRENT_DATE) 
- to get year use YEAR(date)
- to get month use MONTH(date)
- to get quarter use QUARTER(date)


For sector or sub sector information:
- USE both sector and sub_sector columns in the query. For example:  (sector in ('BioTech & Pharma') OR sub_sector in ('BioTech & Pharma'))
- ACCESS the relevant information to identify the proper sector and or sub sector to query. For example Green Energy could mean Clean Energy, Fintech could mean FinTech software, Biotech could mean BioTech & Pharma, etc
- ONLY use the ICMS_ISSUER table to join and pull the sector and sub_sector columns, so you must join with icms_issuer to access sector and sub sector information

Remember:
- if joining with icms_issuer table use "slug" column
    - secondary_transactions join issuer_id_name = slug
    - funding_rounds join issuer_id_name = slug
    - ioi_history join issuer_id_name = slug
    - public_marks join isser_id = slug
    - forge_prices join isser_id = slug
    - vwap join isser_slug = slug
- to use the secondary_transactions table for trade information, not forge_prices or vwap
- to use today's date as the current date
- if output in cents convert to dollars
- DO NOT use alias in GROUP BY or ORDER BY clauses. This will throw an error
- write case statement if dividng by a number to account errors
    - for example,  CASE WHEN total_shares = 0 OR total_shares IS NULL THEN 0 ELSE valuation / total_shares END AS value_per_share

Pay attention to use only the column names that you can see in the schema description. Be careful to not query for columns that do not exist. Pay attention to which column is in which table. Also, qualify column names with the table name when needed. You are required to use the following format, each taking one line:

Question: Question here
SQLQuery: SQL Query to run
SQLResult: Result of the SQLQuery
Answer: Final answer here

Only use tables listed below.
{schema}

Question: {query_str}
SQLQuery: 
"""

text2sql_prompt = PromptTemplate(
    text2sql_prompt_str,
)

response_synthesis_prompt_str = (
    "Given an input question, synthesize a response from the query results.\n"
    "Query: {query_str}\n"
    "SQL: {sql_query}\n"
    "SQL Response: {context_str}\n"
    "Response: "
)
response_synthesis_prompt = PromptTemplate(
    response_synthesis_prompt_str,
)


qp = QP(
    modules={
        "input": InputComponent(),
        "table_retriever": obj_retriever,
        "table_output_parser": table_parser_component,
        "text2sql_prompt": text2sql_prompt,
        "text2sql_llm": llm_to_use,
        "sql_output_parser": sql_parser_component,
        "sql_retriever": sql_retriever,
        "response_synthesis_prompt": response_synthesis_prompt,
        "response_synthesis_llm": llm_to_use,
    },
    verbose=True,
)

qp.add_link("input", "table_retriever")
qp.add_link("input", "table_output_parser", dest_key="query_str")
qp.add_link("table_retriever", "table_output_parser", dest_key="table_schema_objs")
qp.add_link("input", "text2sql_prompt", dest_key="query_str")
qp.add_link("table_output_parser", "text2sql_prompt", dest_key="schema")
qp.add_chain(["text2sql_prompt", "text2sql_llm", "sql_output_parser", "sql_retriever"])
qp.add_link("sql_output_parser", "response_synthesis_prompt", dest_key="sql_query")
qp.add_link("sql_retriever", "response_synthesis_prompt", dest_key="context_str")
qp.add_link("input", "response_synthesis_prompt", dest_key="query_str")
qp.add_link("response_synthesis_prompt", "response_synthesis_llm")


# Length of "assistant: " (including space)
def parse_llm_output_string(response):
    text = str(response)
    assistant_prefix_length = len("assistant: ")

    # Check if the string starts with "assistant: " (case-sensitive)
    if text.lower().startswith("assistant: "):
        # Slice the string to remove the prefix
        return text[assistant_prefix_length:]
    else:
        # String doesn't start with the prefix, keep it as is
        return text


# summarize chat history to keep state context
def summarize_chat_history(llm, chat_history_list, n=20):
    chat_history_len = len(chat_history_list)
    chat_history = chat_history_list[1:][(chat_history_len - n) :]

    return llm.complete(f"Summarize: {chat_history}")


if prompt := st.chat_input(
    "Your question"
):  # Prompt for user input and save to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

for message in st.session_state.messages:  # Display the prior chat messages
    with st.chat_message(message["role"]):
        st.write(message["content"])

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = qp.run(query=f"{prompt}")
                print(response)
                # if len(st.session_state.messages) <= 2:
                #     response = qp.run(query=f"{prompt}")
                # else:
                #     # Add chat context history to chat after initial prompt
                #     response = qp.run(
                #         query=f"{prompt}\n Chat history context: {summarize_chat_history(llm_to_use, st.session_state.messages)}"
                #     )

                content = parse_llm_output_string(response)
            except:
                content = "Sorry, I'm not able to answer your question."

            st.write(content)
            message = {"role": "assistant", "content": content}
            st.session_state.messages.append(message)  # Add response to message history
