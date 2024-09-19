import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from dotenv import load_dotenv

load_dotenv()


def handler(event, context):

    # Initialize clients for S3 and SES
    s3_client = boto3.client("s3")
    ses_client = boto3.client("ses")

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    # if space in filename, event inserts '+'. This leads to job failure since filename cannot be found.
    key = key.replace("+", " ")
    print(bucket, key)

    filename = key.split("/")[-1].split(".xlsx")[0]

    try:
        # Temporary file path in Lambda's /tmp/ directory
        local_file_path = f"/tmp/{filename}.xlsx"

        # Download the file from S3 to /tmp/
        s3_client.download_file(bucket, key, local_file_path)
        # print(hello)
        # Read the downloaded file
        with open(local_file_path, "rb") as f:
            file_data = f.read()

        # Email details
        SENDER_EMAIL = os.getenv("SENDER_EMAIL")
        TO_RECIPIENTS_EMAIL = os.getenv("TO_RECIPIENTS_EMAIL")
        CC_RECIPIENTS_EMAIL = os.getenv("CC_RECIPIENTS_EMAIL")

        subject = f"COI Output Attached - {filename}"
        body_text = f"Attaching the Excel workbook for {filename}"

        recipients = TO_RECIPIENTS_EMAIL.split(",") + CC_RECIPIENTS_EMAIL.split(",")

        # Create a multipart email
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = TO_RECIPIENTS_EMAIL
        msg["Subject"] = subject
        msg["Cc"] = CC_RECIPIENTS_EMAIL

        # Attach the body text
        body = MIMEText(body_text)
        msg.attach(body)

        # Attach the Excel file
        attachment = MIMEApplication(file_data)
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(local_file_path),
        )
        msg.attach(attachment)

        # Send the email
        response = ses_client.send_raw_email(
            Source=SENDER_EMAIL,
            Destinations=recipients,
            RawMessage={
                "Data": msg.as_string(),
            },
        )
        print("email sent")
        return {
            "statusCode": 200,
            "body": f"Email sent! Message ID: {response['MessageId']}",
        }
    except Exception as e:

        SENDER_EMAIL_ERROR = os.getenv("SENDER_EMAIL")
        TO_RECIPIENTS_EMAIL_ERROR = os.getenv("TO_RECIPIENTS_EMAIL")

        subject = f"COI Email not sent - {filename}"
        body = f"Error: {e}"

        message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}}

        # Send the email
        response = ses_client.send_email(
            Source=SENDER_EMAIL_ERROR,
            Destination={
                "ToAddresses": [
                    TO_RECIPIENTS_EMAIL_ERROR,
                ]
            },
            Message=message,
        )

        print("error email sent")

        return {
            "statusCode": 501,
            "body": f"Error: email with excel attachment not sent!",
        }


if __name__ == "__main__":
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "coi-reader-dev-coireaderdeve59305f7-bdrj9eeywtdz"
                    },
                    "object": {
                        "key": "outputs/excel/aven 2024-04-01 COI/gpt-4o/aven 2024-04-01 COI.xlsx"
                    },
                }
            }
        ]
    }

    handler(event, "context")
