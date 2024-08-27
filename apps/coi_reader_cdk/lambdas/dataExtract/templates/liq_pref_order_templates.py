raw_extract_template = """
You are a helpful assistant. Use the document provided (see XML tags) to summarize the liquidation preference order for the preferred shareholders. The liquidation preference order will outline the order the various series of preferred stock will be paid out in the event of a liquidation event.

Make sure to:
- Capture all mentions of “pari passu”
- Quote the specific text from the document and where it was found in the summary
- Account for all series of preferred stock ({preferred_shares_list})
- Do not make up or imply information.

Provide the summary in the final answer. I do not want a ranking of the series of preferred stock.

<document>
{document}
</document>

<final_answer>
"""
raw_extract_output_format = ""

precise_extract_template = """
You are a helpful assistant. Use the document to understand the liquidation preference order for each series of preferred stock ({preferred_shares_list}) based on payment priority. 

Make sure to:
- “pari passu" means the series of preferred stock have the same ranking
- If conflicting information in the summary, default to information in quotes
- Incorporate for all series of preferred stock in final answer. Do not group series
- Do not make up or imply any answers

Provide only the final answer in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```": {output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
    "liquidation_preference_order_output": {
        "preferred_stock_type1": {"rank":1},
        "preferred_stock_type2": {"rank":2},
        "preferred_stock_type3": {"rank":2},
        "preferred_stock_type4": {"rank":3}
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
"liquidation_preference_order_eval": {"preferred_stock_type1": {"data_extract_rank": value,
                                            "ground_truth_liq_pref_order": value
                                            },
                    "preferred_stock_type2": {"data_extract_rank": value,
                                        "ground_truth_liq_pref_order": value
                                        },
                    ...
                }                                            
}                           
"""
