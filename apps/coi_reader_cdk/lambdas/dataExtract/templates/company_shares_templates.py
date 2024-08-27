raw_extract_template = """

You are a helpful assistant. Please extract the following details listed below from the document along with the specific supporting text. The details are found within the details XML tabs, and the document is found within the document XML tags. 

<document>
{document}
</document>

<details>
1a. company_name: The company's name. For example, ABC Corp.
1b. company_name_supporting_text: Quote the specific text used to extract the company_name.
2a. preferred_stock_names: Names of each type of Preferred Stock Shares. For example, ['Series A', 'Series B', 'Series B-1', 'Series 1']
2b. preferred_stock_names_supporting_text: Quote the specific text used to extract the series_names_details.
3a. common_shares: Total number of common shares. For example, 5,000. Only provide the numeric value.
3b. common_shares_supporting_text: Quote the specific text used to extract the common_shares.
4a. shares_per_preferred_stock: Total number of shares for each type of preferred stock. For example, ('Series A': '1,000', 'Series A-1': '200', 'Series B(a)': '10,000')
4b. shares_per_preferred_stock_supporting_text: Quote the specific text used to extract the shares_per_preferred_stock.
</details>

Finally, take extracted details and generate the final output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>"""

raw_extract_output_format = """
{
"company_name": string,
"company_name_supporting_text": string,
"preferred_stock_names": ["preferred_stock_type1","preferred_stock_type2", etc.],
"preferred_stock_names_supporting_text": string,
"common_shares": string,
"common_shares_supporting_text": string,
"preferred_shares_per_preferred_stock": {"preferred_stock_name1": {"number_of_shares": string, "supporting_text": string},
                                        "preferred_stock_name2": {"number_of_shares": string, "supporting_text": string},
                                        ...
                                        }                                            
}
"""

precise_extract_template = """
You are a helpful assistant. I want you to extract and reformat certain items from the document provided (see document XML tags).

Below are the items to change with specific instructions.
1. Do not change the company name
2. Remove all supporting text fields
3. "preferred_stock_names": Remove extraneous words like 'Preferred Stock'. The output should only contain "Series" and the name (i.e., Series A, Series B, Series C-1)
4. "common_shares":  Extract only the number of common shares from the common_share field. If no value retun 'Not found'.
5. "preferred_shares_per_preferred_stock": Extract value from number_of_shares field. If no value retun 'Not found'.

The final answer should contain the updated json object in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"company_name": string,
"preferred_stock_names": ["preferred_stock_type1","preferred_stock_type2", etc.],
"common_shares": string,
"preferred_shares_per_preferred_stock": {"preferred_stock_name1": {"number_of_shares": string},
                                         "preferred_stock_name2": {"number_of_shares": string},
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

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>
"""

eval_output_format = """
{
    "company_name": {"data_extract": string,
                            "ground_truth": string,
                            "match": int
                            },             
    "preferred_stock_names": {"data_extract": list,
                            "ground_truth": list,
                            "match": int
                            },
    "common_shares": {"data_extract" string,
                    "ground_truth": string,
                    "match": int
                    }, 
    "preferred_shares": {"preferred_stock_name1": {"data_extract": string,
                                        "ground_truth": string,
                                        "match": int
                                        },
                    "preferred_stock_name2": {"data_extract": string,
                                        "ground_truth": string,
                                        "match": int
                                        },
                    ...                    
                    }                                                          
}                           
"""
