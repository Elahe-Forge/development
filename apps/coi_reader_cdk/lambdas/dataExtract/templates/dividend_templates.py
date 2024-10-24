raw_extract_template = """
You are a helpful assistant. Using the document provided (document XML tags) summarize all of information related to dividends. Make sure to capture the specific dividend rate for each series of preferred stock ({preferred_shares_list})

Do not make up any information and quote the specific text from the document for reference. Only factual information sourced directly from the document.

<document>
{document}
</document>

<final_answer>"""

raw_extract_output_format = ""

# had to modify this template because wasn't always finding the document since it is so far down the list of instructions in the prompt
precise_extract_template = """
You are a helpful assistant. From the document (see document XML tags) I want you to:

1. Find the dividend as percentage of issue price (percentage) or dividend rate per share ($) for each series of preferred stock ({preferred_shares_list}). Do not make up or imply any information.
2. Determine whether the dividend is cumulative, either Yes or No. Key words that mean dividend is cumulative (“Cumulative”, “Cumulative Preferred Stock”, “Accruing Dividends”, “shall accrue”). Default to "No" if no mention of cumulative dividends in the document.

Make sure to:
1. Extract the dividend as percentage of issue price (dividend_pct) or dividend rate per share (dividend_per_share). Convert value to float (i.e. 5% = 0.05, 0.1234 = 0.1234). If no dividend value return 0.
2. If document mentions all series of preferred stock are entitled to a dividend (i.e., 5%), then each series of preferred stock receives that dividend (i.e. preferred_stock1: 5%, preferred_stock2: 5%, etc.)
4. If dividend_pct = 0 and dividend_per_share = 0 then "dividend_cumulative" = "No"  
5. Include all series of preferred stock
6. Do not make up or imply any information.

Provide the output in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}. Follow the naming convention exactly in the markdown code snippet. Only change the preferred stock name and the values for the dividend_pct, dividend_per_share, and dividend_cumulative.

If no dividend information found for all series of preferred stock return "preferred_stock1":("dividend_pct":0, "dividend_per_share":0, "dividend_cumulative": "No"), "preferred_stock2":("dividend_pct":0, "dividend_per_share":0, "dividend_cumulative": "No"), etc.

<document>
{document}
</document>

<final_answer>
"""

precise_extract_output_format = """
{
"dividend_output": {
                        "preferred_stock_name1": {
                            "dividend_pct": float,
                            "dividend_per_share": float,
                            "dividend_cumulative": string
                        },
                        "preferred_stock_name2": {
                            "dividend_pct": float,
                            "dividend_per_share": float,
                            "dividend_cumulative": string                
                        },
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
    "dividend_eval": {"preferred_stock_name1": {"data_extract_issue_price": value,
                                        "data_extract_dividend_pct": value,
                                        "data_extract_dividend_per_share": value,
                                        "data_extract_cumulative": value,
                                        "ground_truth_dividend": value,
                                        "ground_truth_cumulative": value
                                    },
                    "preferred_stock_name2": {"data_extract_issue_price": value,
                                        "data_extract_dividend_pct": value,
                                        "data_extract_dividend_per_share": value,
                                        "data_extract_cumulative": value,
                                        "ground_truth_dividend": value,
                                        "ground_truth_cumulative": value
                                    },
                    ...                    
                    }                                               
}                           
"""
