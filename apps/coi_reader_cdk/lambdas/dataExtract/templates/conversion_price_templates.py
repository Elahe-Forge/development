raw_extract_template = """
You are a helpful assistant. Please extract the following details listed below from the document for each series of preferred stock ({preferred_shares_list}) along with the specific supporting text. The details are found within the details XML tabs, and the document is found within the document XML tags. 

<document>
{document}
</document>

<details>
1. Conversion price for each type of preferred stock. For example, ('Series A': '10.50', 'Series A-1': '7.59', 'Series B(a)': '0.691'). The conversion price can sometimes equal the original issue price.
2. Quote the specific text used to extract the conversion price.
</details>

Finally, take extracted details and generate the final output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

Do not make up or imply any information.

<final_answer>"""

raw_extract_output_format = """
{
"conversion_price_per_preferred_stock": {"preferred_stock_name1": {"conversion_price": string, "supporting_text": string},
                                         "preferred_stock_name2": {"conversion_price": string, "supporting_text": string},
                                            ...
                                        }                                                                                                                                                                                                                                                                     
}
"""

precise_extract_template = """
You are a helpful assistant. I want you to extract and reformat certain items from the document provided (see document XML tags).

Below are the items to change with specific instructions.
1. Remove all supporting text fields
2. "preferred_stock_names": Remove extraneous words like 'Preferred Stock'. The output should only contains the series name (i.e., Series A, Series B, Series C-1)
3. "conversion_price_per_preferred_stock": Extract value from conversion_price field and convert value to float. If no value retun 'Not found'.

The final answer should contain the updated json object in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"conversion_price_per_preferred_stock": {"preferred_stock_name1": {"conversion_price": float},
                                         "preferred_stock_name2": {"conversion_price": float}
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

data_extract_conversion_ratio = data_extract_issue_price / data_extract_conversion_price

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>
"""

eval_output_format = """
{                                  
    "conversion_ratio_eval": {"preferred_stock_name1": {"data_extract_conversion_price": value,
                                            "data_extract_issue_price": value,
                                            "data_extract_conversion_ratio": value,
                                            "ground_truth_conversion_ratio": value
                                            },
                        "preferred_stock_name2": {"data_extract_conversion_price": value,
                                            "data_extract_issue_price": value,
                                            "data_extract_conversion_ratio": value,
                                            "ground_truth_conversion_ratio": value
                                            },
                        ...
                        }                                                           
}                           
"""
