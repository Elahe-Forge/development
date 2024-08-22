import json

import boto3
from langchain_community.document_loaders import AmazonTextractPDFLoader

s3_client = boto3.client("s3")
textract_client = boto3.client("textract")


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

        file_path = f"s3://{bucket}/{key}"
        print(file_path)

        # using Amazon Textract to convert PDF to text
        textract_client = boto3.client("textract", region_name="us-west-2")

        # extracts text from PDF document using Amazon Textract
        loader = AmazonTextractPDFLoader(file_path, client=textract_client)

        # loads document
        document = loader.load()

        # loops through pages and joins document content
        ttl_document_text = "".join([page.page_content for page in document])

        filename = key.split("/")[-1].split(".pdf")[0]
        filename = f"{filename}.txt"
        output_key = f"outputs/document_txts/{filename}"

        # Upload the text file to S3
        response = s3_client.put_object(
            Bucket=bucket, Key=output_key, Body=ttl_document_text
        )
        print(f"File saved to S3: {bucket}/{output_key}")

    except Exception as e:
        print(f"Error in processing PDF to txt: {e}")

    # print(f"Extracted text {len(text)} length. Text header:", text[:200])
    return {"statusCode": 200, "body": json.dumps("Text extraction complete!")}
