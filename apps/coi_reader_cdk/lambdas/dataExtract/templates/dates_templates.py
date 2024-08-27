raw_extract_template = """

You are a helpful assistant. Please extract the following details listed below from the document along with the specific supporting text. The details are found within the details XML tabs, and the document is found within the document XML tags. 

<document>
{document}
</document>

<details>
1a. document_delivery_date: Document delivery date, formatted in YYYY-MM-DD format. For example, 2020-10-01
1b. document_delivery_date_supporting_text: Quote the specific text used to extract the coi_delivery_date_details.
2a. incorporation_date: Incorporation date, formatted in YYYY-MM-DD format. For example, 2020-10-01
2b. incorporation_date_supporting_text: Quote the specific text used to extract the coi_incorporation_date_details.
</details>

Finally, take extracted details and generate the final output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>"""

raw_extract_output_format = """
{
"document_delivery_date": date,
"document_delivery_date_supporting_text": string,
"incorporation_date": date,
"incorporation_supporting_text": string                                   
}
"""

precise_extract_template = """
You are a helpful assistant. I want you to extract and reformat certain items from the document provided (see document XML tags).

Below are the items to change with specific instructions.
1. Capture only the dates

The final answer should contain the updated json object in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"document_delivery_date": string,
"incorporation_date": string
}
"""

eval_template = """
You are a helpful assistant. I want you to use the data extraction output and compare the results to the ground truth. Both are provided below.

<data_extract_output>
{data_extract_output}
</data_extract_output>

<ground_truth>
{ground_truth}
</ground_truth>

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>
"""

eval_output_format = """
{
    "document_delivery_date": {"data_extract": string,
                        "ground_truth": string,
                        "match": int
                        },
    "incorporation_date": {"data_extract": string,
                        "ground_truth": string,
                        "match": int
                        }                        
}                           
"""
