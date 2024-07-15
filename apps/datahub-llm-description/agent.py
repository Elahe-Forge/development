from llama_index.core import Settings
from llama_index.llms.ollama import Ollama

from llama_index.core.tools import QueryEngineTool, ToolMetadata
#from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.prompts import PromptTemplate

from vectore_store import get_index
import logging
import os
from dotenv import load_dotenv


load_dotenv()
model = os.getenv('OLLAMA_LLM_MODEL')
base_url = os.getenv('OLLAMA_LLM_URL')

logger = logging.getLogger(__name__)


if os.getenv('LLM_PROVIDER') == "ollama":
    llm = Ollama(model=model,
                        base_url=base_url,
                        request_timeout=360.0)
    Settings.llm = llm
    
if os.getenv('LLM_PROVIDER') == "bedrock":
    raise Exception("bedrock not yet implemented")


query_engine = get_index().as_query_engine()

query_engine_tools = [
    QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="forge_knowledge",
            description=(
                "Provides information about forge and private markets schemas, documentation and internal knowledge "
                "Use a detailed plain text question as input to the tool."
            ),
        ),
    ),
]


class ColumnDescriptionAgent:
  def __init__(self):
    self.agent = ReActAgent.from_tools(
        query_engine_tools,
        llm=llm,
        verbose=True,
    )
    self.prompt_template = PromptTemplate(
        "Generate an appropriate column description for the following table {table_name} and column {column_name}, \
        only return a small definition related to {column_name} without returning information about the table {table_name} \
        example: Id represent the unique key of the table {table_name}"
    )
    

  def describe_column(self, table_name, column_name):
    prompt = self.prompt_template.format(table_name=table_name, column_name=column_name)
    try:
        return self.agent.query(prompt).response
    except ValueError as e:
        print(str(e))
        #### fallback to basic RAG lookup
        return self.zero_shot_rag_answer(table_name, column_name)
    
  def zero_shot_rag_answer(self, table_name, column_name):
      prompt = self.prompt_template.format(table_name=table_name, column_name=column_name)
      logger.info(f"Performing zero shot rag on {table_name}.{column_name}")
      return str(query_engine.query(prompt))
  
class TableDescriptionAgent:
  def __init__(self):
    self.agent = ReActAgent.from_tools(
        query_engine_tools,
        llm=llm,
        verbose=True,
    )
    self.prompt_template = PromptTemplate(
        "Generate an appropriate description for the following table {table_name} having these fields {fields}, \
        only return a short definition related to the table {table_name} without returning information about the fields in particular \
        example: The table transactions contains all the trades that ever happened"
    )
    

  def describe_table(self, table_name, fields):
    prompt = self.prompt_template.format(table_name=table_name, fields=fields)
    try:
        return self.agent.query(prompt).response
    except ValueError as e:
        print(str(e))
        #### fallback to basic RAG lookup
        return self.zero_shot_rag_answer(table_name, fields)
    
  def zero_shot_rag_answer(self, table_name, fields):
      prompt = self.prompt_template.format(table_name=table_name, fields=fields)
      return str(query_engine.query(prompt))

class BusinessGlossaryAgent:
  def __init__(self):
    self.agent = ReActAgent.from_tools(
        query_engine_tools,
        llm=llm,
        verbose=True,
    )
    self.prompt_template = PromptTemplate(
        "Find the appropriate business glossary for the following {table_name} having these fields {fields}, \
        only return the business glossary term and nothing else. \
        example: data-product"
    )
    

  def define_business_glossary(self, table_name, fields):
    prompt = self.prompt_template.format(table_name=table_name, fields=fields)
    try:
        return self.agent.query(prompt).response
    except ValueError as e:
        print(str(e))
        #### fallback to basic RAG lookup
        return self.zero_shot_rag_answer(table_name, fields)
    
  def zero_shot_rag_answer(self, table_name, fields):
      prompt = self.prompt_template.format(table_name=table_name, fields=fields)
      return str(query_engine.query(prompt))
  
class CompanyDataClassificationAgent:
  def __init__(self):
    self.agent = ReActAgent.from_tools(
        query_engine_tools,
        llm=llm,
        verbose=True,
    )
    self.prompt_template = PromptTemplate(
        "Find the appropriate Data Classification for the following {table_name} having these fields {fields}, \
        only return the Data Classification term and nothing else. The only 4 options are the following: Confidential, Restricted, Internal, Public. \
        example response: Confidential"
    )
    

  def define_data_classification(self, table_name, fields):
    prompt = self.prompt_template.format(table_name=table_name, fields=fields)
    try:
        return self.agent.query(prompt).response
    except ValueError as e:
        print(str(e))
        #### fallback to basic RAG lookup
        return self.zero_shot_rag_answer(table_name, fields)
    
  def zero_shot_rag_answer(self, table_name, fields):
      prompt = self.prompt_template.format(table_name=table_name, fields=fields)
      return str(query_engine.query(prompt))
       