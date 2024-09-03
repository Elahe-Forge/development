import json

import helpers.transformers as transformers
import helpers.utils as utils
from openpyxl import load_workbook
from openpyxl.comments import Comment


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

        json_data = utils.load_s3_json_obj(bucket, key)  # load config file from event

        precise_df, preferred_shares_list = transformers.generate_precise_df(
            bucket, json_data
        )
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

        return {"statusCode": 500, "body": json.dumps("Data extraction NOT complete!")}


# For testing purposes
# if __name__ == "__main__":
#     event = {
#         "bucket": "coi-reader-dev-coireaderdeve59305f7-bdrj9eeywtdz",
#         "key": "outputs/config_json/tae-technologies 2024-08-23 COI/gpt-4o/config.json",
#         "test": 1,
#     }

#     handler(event, "context")
