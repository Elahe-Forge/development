raw_extract_template = """
You are a helpful assistant. Use the document provided (see XML tags) to summarize the distribution of remaining assets information. Do not include any information related to liquidation preference, dividend payments or dividend distributions.

After the description of liquidation preference the document will describe who has rights to the remaining distribution of assets or funds. In some cases only Common Shareholders have rights, in other cases Preferred Shareholders and Common Shareholders have rights, and finally in other cases the document will explicitly state the series of preferred stock ({preferred_shares_list}) along with Common Shareholders has rights. 

Make sure to capture if any caps exists within the distribution of remaining assets, specifically participation caps or maximum participation amounts.

The summary needs to contain specific quotes from the document for reference. Do not make up or imply any information.

<document>
{document}
</document>

<final_answer>
"""

raw_extract_output_format = ""

precise_extract_template = """
You are a helpful assistant. Using the document (see document XML tags) extract the particpation cap or maximum participation amount for each series of preferred stock ({preferred_shares_list}). 

Remember:
- The participation cap or maximum participation amount can be a multiple, percentage, or conversion rate
- If no participation cap or maximum participation amount found return 0
- Capture all series of preferred shares in the final answer

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
    {
    "participation_cap": {"preferred_stock_name1": {"cap": float},
                          "preferred_stock_name2": {"cap": float},
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
"participation_cap_eval": {"preferred_stock1": {"data_extract": value,
                                                "ground_truth": value
                                                },
                    "preferred_stock2": {"data_extract": value,
                                        "ground_truth": value
                                        },
                    ...
                }                                            
}                           
"""
