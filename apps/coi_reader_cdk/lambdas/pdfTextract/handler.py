import os

import boto3
from dotenv import load_dotenv
from langchain_community.document_loaders import AmazonTextractPDFLoader

load_dotenv()


def handler(event, context):
    s3_client = boto3.client("s3")
    ses_client = boto3.client("ses")
    textract_client = boto3.client("textract")

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    # if space in filename, event inserts '+'. This leads to job failure since filename cannot be found.
    key = key.replace("+", " ")
    filename = key.split("/")[-1].split(".pdf")[0]

    file_path = f"s3://{bucket}/{key}"
    print(file_path)

    try:
        # using Amazon Textract to convert PDF to text
        textract_client = boto3.client("textract", region_name="us-west-2")

        # extracts text from PDF document using Amazon Textract
        loader = AmazonTextractPDFLoader(file_path, client=textract_client)

        # loads document
        document = loader.load()

        # loops through pages and joins document content
        ttl_document_text = "".join([page.page_content for page in document])

        filename = f"{filename}.txt"
        output_key = f"outputs/document_txts/{filename}"

        # Upload the text file to S3
        response = s3_client.put_object(
            Bucket=bucket, Key=output_key, Body=ttl_document_text
        )
        print(f"File saved to S3: {bucket}/{output_key}")

        return {"statusCode": 200, "body": "Text extraction complete!"}

    except Exception as e:
        print(f"Error in processing PDF to txt: {e}")

        SENDER_EMAIL = os.getenv("SENDER_EMAIL")
        TO_RECIPIENTS_EMAIL = os.getenv("TO_RECIPIENTS_EMAIL")

        # sender = "elahe.paikari@forgeglobal.com"
        # recipient = "bo.brandt@forgeglobal.com"
        subject = f"PDF to Text Error - {filename}"
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

        return {
            "statusCode": 501,
            "body": "Error! Text extraction did not complete!",
        }


# For testing purposes
if __name__ == "__main__":

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "coi-reader-dev-coireaderdeve59305f7-bdrj9eeywtdz"
                    },
                    "object": {"key": "inputs/pdfs/kong 2024-08-06 COI.pdf"},
                }
            }
        ]
    }

    handler(event, None)
