raw_extract_template = """
You are a helpful assistant. Please extract the following details listed below from the document for each series of preferred stock ({preferred_shares_list}) along with the specific supporting text. The details are found within the details XML tabs, and the document is found within the document XML tags. 

<document>
{document}
</document>

<details>
1a. company_name: The company's name. For example, ABC Corp.
2a. preferred_stock_names: Names of each type of Preferred Stock Shares. For example, ['Series A', 'Series B', 'Series B-1']
3a. issue_price_per_preferred_stock: Original issue price for each series of preferred stock. For example, ('Series A': '10.00', 'Series A-1': '9.51', 'Series B(a)': '0.198')
3b. issue_price_per_preferred_stock_supporting_text: Extract the specific text used to find the issue price for the series of preferred stock.
</details>

Finally, take extracted details and generate the final output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>"""

raw_extract_output_format = """
{
"issue_price_per_preferred_stock": {"preferred_stock_name1": {"issue_price": string, "supporting_text": string},
                                    "preferred_stock_name2": {"issue_price": string, "supporting_text": string},
                                     ...
                                    }                                                                                                                                                                                                                                                                     
}
"""

precise_extract_template = """
You are a helpful assistant. I want you to extract and reformat certain items from the document provided (see document XML tags).

Below are the items to change with specific instructions.
1. Remove all supporting text fields
2. "preferred_stock_names": Remove extraneous words like 'Preferred Stock'. The output should only contains the series name (i.e., Series A, Series B, Series C-1)
3. "issue_price_per_preferred_stock": Extract value from issue_price field and convert value to float. If no value retun 'Not found'.

The final answer should contain the updated json object in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"issue_price_per_preferred_stock": {"preferred_stock_name1": {"issue_price": float},
                                    "preferred_stock_name2": {"issue_price": float},
                                    ...
                                    }                                 
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

If ground truth value is nan return 0.

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>
"""

eval_output_format = """
{                                 
    "issue_price_eval": {"preferred_stock_name1": {"data_extract": value,
                                        "ground_truth": value,
                                        "match": int
                                        },
                    "preferred_stock_name2": {"data_extract": value,
                                        "ground_truth": value,
                                        "match": int
                                        },
                    ...                    
                    }                                                          
}                           
"""
