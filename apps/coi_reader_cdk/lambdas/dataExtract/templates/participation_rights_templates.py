raw_extract_template = """
You are a helpful assistant. Use the document provided (see XML tags) to summarize the liquidation preference and the distribution of remaining assets information. Do not include any information related to dividend payments or dividend distributions.

After the description of liquidation preference the document will describe who has rights to the remaining distribution of assets or funds. In some cases only Common Shareholders have rights, in other cases Preferred Shareholders and Common Shareholders have rights, and finally in other cases the document will explicitly state the series of preferred stock ({preferred_shares_list}) along with Common Shareholders has rights.

The summary needs to contain specific quotes from the document for reference. Do not make up or imply any information.

<document>
{document}
</document>

<final_answer>
"""
raw_extract_output_format = ""

precise_extract_template = """
You are a helpful assistant. Using the document (see document XML tags) determine whether each series of preferred stock ({preferred_shares_list}) participate in the distribution of remaining assets, either 'Yes' or 'No'.

Remember:
- Consider only the distribution of remaining assets information, not liquidation preferences. 
- Identify the series of preferred shares where the remaining assets are distributed amongst the holders
- Distribution of remaining assets to ONLY common stock means all series do not participate in the distribution of remaining assets
- “Preferred Stock AND Common Stock”, means all the series of preferred stock participates in the distribution
- Capture all series of preferred shares in the final answer

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"participation_rights": {"preferred_stock_name1": {"participation": "Yes"},
                        "preferred_stock_name2": {"participation": "No"},
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

If ground truth value is nan return No.

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

<final_answer>
"""

eval_output_format = """
{
"participation_rights_eval": {"preferred_stock1": {"data_extract": string,
                                            "ground_truth": string
                                            },
                    "preferred_stock2": {"data_extract": string,
                                        "ground_truth": string
                                        },
                    ...
                }                                            
}                           
"""
