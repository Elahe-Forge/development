import json
import os
import re

import boto3
from helpers.readers import DocumentReader

# import json

# import helpers.utils as utils

s3 = boto3.client("s3")


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


def load_and_correct_json(json_string, model_id):
    try:
        # Try to load the JSON string first
        return extract_json_obj(json_string)
    except json.JSONDecodeError:

        try:

            doc_reader = DocumentReader(model_id=model_id)

            template = """
            You are a helpful assistant. Please take the following input text (see document XML tags) and reformat it into a valid JSON object. Currently is not a valid JSON object and contains errors.

            Make sure to:

            1. remove double quotes within double quotes
            2. remove escape characters
            3. Check that it does not contain extract brackets at the end
            4. Check that it does not contain missing brackets at the end

            The final answer should contain the updated json object in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

            <document>
            {document}
            </document>

            <final_answer>
            """

            output_format = """
            {
            "key": "value"
            }
            """

            raw_response = doc_reader.run_llm_extract(
                json_string,
                template,
                output_format,
            )
            # print(raw_response.content)

            return extract_json_obj(raw_response.content)

        except json.JSONDecodeError as e:
            # If it still fails, raise an exception
            raise ValueError(f"Failed to parse JSON: {str(e)}")


def load_file(filepath, model_id, filename, field, extract, as_json=True):
    """Load json object from path"""
    try:
        path = f"{filepath}/{model_id}/{filename}/{field}_{extract}_extract/data.json"
        with open(path, "r") as file:
            json_obj = extract_json_obj(file)
    except Exception as e:
        path = f"{filepath}/{model_id}/{filename}/{field}_{extract}_extract/data.txt"

        with open(path, "r") as file:
            json_str = file.read()
    if as_json:
        return load_and_correct_json(json_str, model_id)
    else:
        return json_str


def load_s3_json_obj(bucket, key):
    # Read the JSON file
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")
    json_data = json.loads(content)

    return json_data


def load_s3_file(bucket, key):

    # Read the file
    response = s3.get_object(Bucket=bucket, Key=key)
    file_content = response["Body"].read().decode("utf-8")

    return file_content


def convert_file_to_json_obj(model_id, file_content):
    try:
        # Try to load the JSON string first
        return extract_json_obj(file_content)
    except json.JSONDecodeError:

        try:

            doc_reader = DocumentReader(model_id=model_id)

            template = """
            You are a helpful assistant. Please take the following input text (see document XML tags) and reformat it into a valid JSON object. Currently is not a valid JSON object and contains errors.

            Make sure to:

            1. remove double quotes within double quotes
            2. remove escape characters
            3. Check that it does not contain extract brackets at the end
            4. Check that it does not contain missing brackets at the end

            The final answer should contain the updated json object in a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":{output_format}

            <document>
            {document}
            </document>

            <final_answer>
            """

            output_format = """
            {
            "key": "value"
            }
            """

            raw_response = doc_reader.run_llm_extract(
                json_string,
                template,
                output_format,
            )
            # print(raw_response.content)

            return extract_json_obj(raw_response.content)

        except json.JSONDecodeError as e:
            # If it still fails, raise an exception
            raise ValueError(f"Failed to parse JSON: {str(e)}")


def extract_supporting_text(d, result=None):
    if result is None:
        result = []
    for key, value in d.items():
        if key == "supporting_text":
            result.append(value)
        elif isinstance(value, dict):
            extract_supporting_text(value, result)
    return result
