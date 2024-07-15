import acryl
import json
import os
import sys
from agent import ColumnDescriptionAgent, TableDescriptionAgent, BusinessGlossaryAgent, CompanyDataClassificationAgent
import logging
from dotenv import load_dotenv


load_dotenv()
write_to_acryl = os.getenv('ACRYL_WRITE') == "True"


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)



def write_to_output(table):
    
    subfolder = table["platform"]
    folder_path = f'output/{subfolder}'
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    filename = table["full_name"]
    file_path = os.path.join(folder_path, f"{filename}.json")
    logger.info(f"write {filename} to output folder")
    with open(file_path, "w") as file:
        json.dump(table, file, indent=2, default=str)


def main():
    data_catalog = {}
    tables = acryl.get_tables() # by default glue only but it can be changed to any platform
    
    for table in tables:
        table_name = table["table_name"]
        table_agent = TableDescriptionAgent()
        business_glossary_agent = BusinessGlossaryAgent()
        classification_agent = CompanyDataClassificationAgent()
        
        logger.info(f"Analyzing {table_name}")
        
        data_catalog[table_name] = {
            "name": table_name,
            "full_name": table["full_name"],
            "platform": table["platform"],
            "description": table_agent.zero_shot_rag_answer(table_name, table["fields"] ),
            "glossary_term": business_glossary_agent.zero_shot_rag_answer(table_name, table["fields"]),
            "data_classification": classification_agent.zero_shot_rag_answer(table_name, table["fields"]),
            "fields": {}
        }
        
        if write_to_acryl:
            acryl.write_table_description(table['urn'], data_catalog[table_name]["description"])
            acryl.add_tag_to_table(table['urn'], "AI Generated")
            acryl.add_glossary_term_to_table(table['urn'], data_catalog[table_name]["glossary_term"])
            acryl.add_glossary_term_to_table(table['urn'], data_catalog[table_name]["data_classification"])
        
        for field in table["fields"]:
            logger.info(f"Analyzing {table_name},{field}")
            agent = ColumnDescriptionAgent()
            #description =  agent.describe_column(table_name, field) # Too slow to use ReAct Agent
            description = agent.zero_shot_rag_answer(table_name, field)
            data_catalog[table_name]["fields"][field]= { "description": description }
            if write_to_acryl:
                acryl.write_column_description(table['urn'], field, description)
            
        write_to_output(data_catalog[table_name])

if __name__ == "__main__":
    main()