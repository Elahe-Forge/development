raw_extract_template = """

You are a helpful assistant. Please extract the following details listed below from the document along with the specific supporting text. The details are found within the details XML tabs, and the document is found within the document XML tags. 

<document>
{document}
</document>

<details>
1. preferred_share_names: Names of each type of Preferred Share. For example, ['Series A', 'Series B', 'Series B-1', 'Series 1']
2. preferred_share_names_supporting_text: Quote the specific text used to extract the preferred_share_names.
</details>

Finally, take extracted details and generate the final output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>"""

raw_extract_output_format = """
{
"preferred_share_names": ["preferred_share_name1","preferred_share_name2", etc.],
"preferred_share_names_supporting_text": string
}
"""

precise_extract_template = """
You are a helpful assistant. I want you to extract and reformat certain items from the document provided (see document XML tags).

Below are the items to change with specific instructions.
1. "preferred_share_names": Remove extraneous words like 'Preferred Stock'. The output should only contain "Series" and the name (i.e., Series A, Series B, Series C-1)

The final answer should contain the updated json object in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"preferred_share_names": ["preferred_share_name1","preferred_share_name2", etc.]
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
    "preferred_share_names": {"data_extract": list,
                            "ground_truth": list,
                            "match": int
                            }                                                    
}                           
"""
