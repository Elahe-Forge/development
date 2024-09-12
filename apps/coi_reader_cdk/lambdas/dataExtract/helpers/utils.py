import json
import os
import re

import boto3


def save_output(obj, file_path: str, as_json: bool = True):
    """Save output locally"""

    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as file:
        if as_json:
            json_obj = extract_json_obj(obj)
            json.dump(json_obj, file, indent=4)
        else:
            file.write(obj)


def save_output_s3(bucket_name, file_key, content, json_file=False):
    try:
        # Create an S3 client
        s3 = boto3.client("s3")

        if json_file:
            # Convert the Python dictionary to a JSON string
            json_data = json.dumps(content)

            # Upload the JSON file to S3
            s3.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=json_data,
                ContentType="application/json",
            )
        else:
            # Upload the text file
            s3.put_object(Bucket=bucket_name, Key=file_key, Body=str(content))

        print(f"File uploaded successfully to s3://{bucket_name}/{file_key}")
    except Exception as e:
        print(f"Error uploading txt file to s3://{bucket_name}/{file_key}: {e}")
        raise e


# Define a function to remove trailing commas from JSON-like strings
def remove_trailing_commas(json_like_str):
    # Regular expression to find trailing commas before a closing bracket or brace
    pattern = re.compile(r",\s*([}\]])")
    # Replace instances found by the pattern with the captured group without the comma
    return pattern.sub(r"\1", json_like_str)


def extract_json_obj(input_str):
    start_index = input_str.find("`json\n") + len("`json\n")
    end_index = input_str.rfind("```")
    json_string = input_str[start_index:end_index]
    cleaned_json_string = remove_trailing_commas(json_string)

    try:
        json_obj = json.loads(cleaned_json_string)
    except:
        json_obj = json.loads(cleaned_json_string + "}")

    return json_obj
