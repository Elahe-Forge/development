raw_extract_template = """
You are a helpful assistant. Use the document provided (see XML tags) to:

1. Find the issue price for each series of preferred shares ({preferred_shares_list})
2. Summarize the liquidation preference information. Do not include any information related to the distribution of remaining assets, which typically follows the liquidiation preference information. 

In the summary make sure to:
- Capture all the numeric values provided in the liquidation preference descriptions. For instance, the liquidation preference can also be known as the applicable preference amount or applicable preference multiple, so you need to capture the associated values.
- Use direct quotes from the document
- Do not make up or imply any information

Provided both answers from #1 and #2 in your final answer.

<document>
{document}
</document>

<final_answer>
"""

raw_extract_output_format = ""

precise_extract_template = """
You are a helpful assistant. Using the document (see document XML tags) extract or compute the liquidation preference multiple for each series of preferred stock ({preferred_shares_list}).

Remember:
- The liquidation prefrence multiple = liquidation preference / original issue price
- The liquidation preference can also be known as the applicable preference amount or applicable preference multiple. Make sure to find this value. If time dependent the current year is 2024.
- If no liquidiation preference information found return 1
- Capture all series of preferred shares in the final answer

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"liquidation_preference": {"preferred_stock_name1": {"multiple": float},
                            "preferred_stock_name2": {"multiple": float},
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
"liquidation_preference_eval": {"preferred_stock1": {"data_extract_multiple": value,
                                            "ground_truth_liq_pref": value
                                            },
                    "preferred_stock2": {"data_extract_multiple": value,
                                        "ground_truth_liq_pref": value
                                        },
                    ...
                }                                            
}                           
"""
