# import csv
import json
from io import StringIO

import boto3
import pandas as pd


def load_file(bucket_name: str, file_key: str) -> dict:

    try:
        s3 = boto3.client("s3")

        # Get the object from S3
        response = s3.get_object(Bucket=bucket_name, Key=file_key)

        # Read the object data as bytes
        data = response["Body"].read()

        # Decode the bytes to a string
        json_data = data.decode("utf-8")

        # Parse the JSON string to a Python dictionary
        config_data = json.loads(json_data)

        print("config_data", config_data)

        return config_data

    except Exception as e:
        print(f"Error handling file: {e}")


def copy_file_new_destination(
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    destination_key: str,
) -> None:
    try:
        s3 = boto3.client("s3")

        copy_source = {"Bucket": source_bucket, "Key": source_key}
        # destination_key = f"outputs/saved_model_config/{job_id}/model_config.json"

        s3.copy(copy_source, destination_bucket, destination_key)
        print(
            f"File copied to destination: s3://{destination_bucket}/{destination_key}"
        )

    except Exception as e:
        print(f"Error handling file: {e}")


def send_sns_notification(topic_arn, message, subject):
    # Send SNS notification
    sns_client = boto3.client("sns")

    sns_client.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message,
    )
    print("Error message sent via SNS")


# Initialize Boto3 S3 client
s3_client = boto3.client("s3")


def read_csv_from_s3(bucket_name, key):
    # Read CSV file from S3
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
    body = csv_obj["Body"]
    csv_string = body.read().decode("utf-8")

    # Create a DataFrame
    df = pd.read_csv(StringIO(csv_string))
    return df


def write_jsonl_to_s3(bucket_name, key, jsonl_data):
    # Convert list of JSON strings to a single JSONL string
    jsonl_string = "\n".join(jsonl_data)

    # Write JSONL string to S3
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=jsonl_string)


def process_csv_to_jsonl(bucket_name, input_key, output_key):
    # Read CSV from S3
    df = read_csv_from_s3(bucket_name, input_key)

    # Convert DataFrame to JSONL format
    jsonl_data = (
        df["inputs"]
        .apply(
            lambda x: json.dumps(
                {
                    "inputs": x,
                    "parameters": {
                        "return_all_scores": True,
                        "truncation": True,
                        "max_length": 512,
                    },
                }
            )
        )
        .tolist()
    )

    # Write JSONL to S3
    write_jsonl_to_s3(bucket_name, output_key, jsonl_data)
    print("jsonl data written to:", bucket_name, output_key)
