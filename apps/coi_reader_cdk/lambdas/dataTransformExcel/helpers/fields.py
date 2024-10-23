precise_fields = {
    "shares_type": {
        "output_file": "company_shares",
        "key_name": "preferred_stock_names",
    },
    "preferred_shares": {
        "output_file": "company_shares",
        "key_name": "preferred_shares_per_preferred_stock",
        "data_extract": "number_of_shares",
    },
    "issue_price": {
        "output_file": "issue_price",
        "key_name": "issue_price_per_preferred_stock",
        "data_extract": "issue_price",
    },
    "conversion_price": {
        "output_file": "conversion_price",
        "key_name": "conversion_price_per_preferred_stock",
        "data_extract": "conversion_price",
    },
    "liq_pref_order": {
        "output_file": "liq_pref_order",
        "key_name": "liquidation_preference_order_output",
        "data_extract": "rank",
    },
    "liq_pref": {
        "output_file": "liq_pref",
        "key_name": "liquidation_preference",
        "data_extract": "multiple",
    },
    "participation_cap": {
        "output_file": "participation_cap",
        "key_name": "participation_cap",
        "data_extract": "cap",
    },
    "participation_rights": {
        "output_file": "participation_rights",
        "key_name": "participation_rights",
        "data_extract": "participation",
    },
    "dividend_pct": {
        "output_file": "dividends",
        "key_name": "dividend_output",
        "data_extract": "dividend_pct",
    },
    "dividend_per_share": {
        "output_file": "dividends",
        "key_name": "dividend_output",
        "data_extract": "dividend_per_share",
    },
    "dividend_cumulative": {
        "output_file": "dividends",
        "key_name": "dividend_output",
        "data_extract": "dividend_cumulative",
    },
}


raw_fields = {
    "shares_type": {
        "output_file": "preferred_share_names",
    },
    "preferred_shares": {
        "output_file": "company_shares",
        "key_name": "preferred_shares_per_preferred_stock",
        "data_extract": "supporting_text",
    },
    "issue_price": {
        "output_file": "issue_price",
        "key_name": "issue_price_per_preferred_stock",
        "data_extract": "supporting_text",
    },
    "conversion_price": {
        "output_file": "conversion_price",
        "key_name": "conversion_price_per_preferred_stock",
        "data_extract": "supporting_text",
    },
    "liq_pref_order": {
        "output_file": "liq_pref_order",
    },
    "liq_pref": {
        "output_file": "liq_pref",
    },
    "participation_cap": {
        "output_file": "participation_cap",
    },
    "participation_rights": {
        "output_file": "participation_rights",
    },
    "dividend_pct": {
        "output_file": "dividends",
    },
    "dividend_per_share": {
        "output_file": "dividends",
    },
    "dividend_cumulative": {
        "output_file": "dividends",
    },
}


other_fields = {
    "company_name": {
        "output_file": "company_shares",
        "key_name": "company_name",
        "supporting_text_field": ["company_name_supporting_text"],
    },
    "common_shares": {
        "output_file": "company_shares",
        "key_name": "common_shares",
        "supporting_text_field": ["common_shares_supporting_text"],
    },
    "incorporation_date": {
        "output_file": "dates",
        "key_name": "incorporation_date",
        "supporting_text_field": [
            "incorporation_date_supporting_text",
            "incorporation_supporting_text",
        ],
    },
    "delivery_date": {
        "output_file": "dates",
        "key_name": "document_delivery_date",
        "supporting_text_field": ["document_delivery_date_supporting_text"],
    },
}
