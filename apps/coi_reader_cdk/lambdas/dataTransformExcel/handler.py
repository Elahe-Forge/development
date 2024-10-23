import json
import os

import boto3
import helpers.transformers as transformers
import helpers.utils as utils
from dotenv import load_dotenv

load_dotenv()


def handler(event, context):

    ses_client = boto3.client("ses")

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    # if space in filename, event inserts '+'. This leads to job failure since filename cannot be found.
    key = key.replace("+", " ")
    print(bucket, key)

    filename = key.split("/")[2]

    try:
        json_data = utils.load_s3_json_obj(bucket, key)  # load config file from event

        precise_df, preferred_shares_list = transformers.generate_precise_df(
            bucket, json_data
        )
        print(preferred_shares_list)
        print("Precise DataFrame generated")

        raw_df = transformers.generate_support_df(
            bucket, json_data, preferred_shares_list
        )
        print("Supporting text DataFrame generated")

        other_fields_dict = transformers.extract_other_fields_dict(bucket, json_data)
        print("Other fields extracted")

        transformers.convert_pandas_to_excel(
            bucket, precise_df, raw_df, other_fields_dict, json_data
        )
        print("Data Extract Transformed to Excel Workbook")

        return {"statusCode": 200, "body": json.dumps("Data extraction complete!")}

    except Exception as e:
        print(f"Error process transform: {e}")

        SENDER_EMAIL = os.getenv("SENDER_EMAIL")
        TO_RECIPIENTS_EMAIL = os.getenv("TO_RECIPIENTS_EMAIL")

        subject = f"Data Transform Excel Error - {filename}"
        body = f"Error: {e}"

        message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}}

        # Send the email
        ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={
                "ToAddresses": [
                    TO_RECIPIENTS_EMAIL,
                ]
            },
            Message=message,
        )

        print("Email sent")

        return {"statusCode": 501, "body": json.dumps("Data extraction NOT complete!")}


# For testing purposes
if __name__ == "__main__":

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "coi-reader-dev-coireaderdeve59305f7-bdrj9eeywtdz"
                    },
                    "object": {
                        "key": "outputs/config_json/liqid 2024-10-11 COI/gpt-4o/config.json"
                    },
                }
            }
        ]
    }

    handler(event, None)
