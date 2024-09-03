import json
import types

import boto3
import helpers.utils as utils
import templates.company_shares_templates as company_shares_templates
import templates.conversion_price_templates as conversion_price_templates
import templates.dates_templates as dates_templates
import templates.dividend_templates as dividend_templates
import templates.issue_price_templates as issue_price_templates
import templates.liq_pref_order_templates as liq_pref_order_templates
import templates.liq_pref_templates as liq_pref_templates
import templates.participation_cap_templates as participation_cap_templates
import templates.participation_rights_templates as participation_rights_templates
import templates.preferred_shares_templates as preferred_share_names_templates
from helpers.readers import DocumentReader

s3_client = boto3.client("s3")


def run_extract(
    label: str,
    model_id: str,
    document: str,
    template_module: types.ModuleType,
    bucket,
    output_path: str,
    pref_shares_info=None,
):
    """Extracts raw and precise data from COI Document"""

    doc_reader = DocumentReader(model_id=model_id)

    # Raw Extract
    raw_label = f"{label}_raw_extract"
    raw_response = doc_reader.run_llm_extract(
        document,
        template_module.raw_extract_template,
        template_module.raw_extract_output_format,
        pref_shares_info,
    )

    raw_output_path = f"{output_path}/{raw_label}/data.txt"

    utils.save_output_s3(bucket, raw_output_path, raw_response.content)

    # Precise Extract
    precise_label = f"{label}_precise_extract"

    precise_response = doc_reader.run_llm_extract(
        raw_response.content,
        template_module.precise_extract_template,
        template_module.precise_extract_output_format,
        pref_shares_info,
    )

    precise_output_path = f"{output_path}/{precise_label}/data.txt"
    utils.save_output_s3(bucket, precise_output_path, precise_response.content)
    return precise_response.content, raw_output_path, precise_output_path


# Create an S3 client
s3_client = boto3.client("s3")


def read_s3_text_file(bucket_name, file_key):
    try:
        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)

        # Read the content of the file
        file_content = response["Body"].read().decode("utf-8")

        return file_content
    except Exception as e:
        print(f"Error reading file from S3: {e}")
        return None


def handler(event, context):
    if "test" in event:
        bucket = event["bucket"]
        key = event["key"]
    else:
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]

    try:
        # if space in filename, event inserts '+'. This leads to job failure since filename cannot be found.
        key = key.replace("+", " ")

        print(bucket, key)

        filename = key.split("/")[-1].split(".txt")[0]
        document_txt = read_s3_text_file(bucket, key)

        model_id = "gpt-4o"
        output_path = f"outputs/data_extracts/{filename}/{model_id}"

        # create a for loop to run extracts...
        inputs = [
            ["company_shares", company_shares_templates, False],
            ["preferred_share_names", preferred_share_names_templates, False],
            ["dates", dates_templates, False],
            ["issue_price", issue_price_templates, True],
            ["conversion_price", conversion_price_templates, True],
            ["dividends", dividend_templates, True],
            ["liq_pref_order", liq_pref_order_templates, True],
            ["liq_pref", liq_pref_templates, True],
            ["participation_rights", participation_rights_templates, True],
            ["participation_cap", participation_cap_templates, True],
        ]

        preferred_shares_data = None
        config_output = {
            "model_id": model_id,
            "document_txt_path": f"s3://{bucket}/{key}",
        }
        for i in inputs[:]:
            label = i[0]
            templates = i[1]

            # determine whether to use preferred_shares_data within input templates
            if i[2]:
                preferred_shares_data_to_use = preferred_shares_data
            else:
                preferred_shares_data_to_use = None

            data_extract, raw_output_path, precise_output_path = run_extract(
                label,
                model_id,
                document_txt,
                templates,
                bucket,
                output_path,
                preferred_shares_data_to_use,
            )

            config_output[label] = {
                "raw_output_path": raw_output_path,
                "precise_output_path": precise_output_path,
            }

            # Extract and save preferred_shares_data
            if label == "preferred_share_names":
                preferred_shares_data = data_extract
                print("preferred shares SAVED")

            print(f"{label} DONE")

        config_output_path = f"outputs/config_json/{filename}/{model_id}/config.json"
        utils.save_output_s3(bucket, config_output_path, config_output, json_file=True)

        return {"statusCode": 200, "body": json.dumps("Data extraction complete!")}

    except Exception as e:
        print(f"Error in extract data from txt file: {e}")
        return {
            "statusCode": 501,
            "body": json.dumps("Error! Data extraction did not complete!"),
        }