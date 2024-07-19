import json
import os
import time

from dotenv import load_dotenv
from sagemaker.huggingface import HuggingFaceModel
from utils import (
    copy_file_new_destination,
    load_file,
    process_csv_to_jsonl,
    send_sns_notification,
)

load_dotenv()

execution_role_arn = os.getenv("TARGET_ROLE_ARN")
topic_arn = os.getenv("TOPIC_ARN")


def handler(event, context):
    try:
        print(json.dumps(event))

        if "test" in event:
            bucket = event["bucket"]
            key = event["key"]

        else:
            bucket = event["Records"][0]["s3"]["bucket"]["name"]
            key = event["Records"][0]["s3"]["object"]["key"]

        job_id = int(time.time())

        jsonl_key = f"outputs/saved_data_jsonl/{job_id}/data.jsonl"

        # Process Data Input CSV to JSONL and save to S3
        process_csv_to_jsonl(bucket, key, jsonl_key)

        data_uri = f"s3://{bucket}/{jsonl_key}"
        print("data_uri", data_uri)

        model_config_key = "inputs/model_config/model_config.json"
        model_config = load_file(bucket, model_config_key)

        model_uri = model_config["model_uri"]
        instance_count = model_config["instance_count"]
        instance_type = model_config["instance_type"]

        transformers_version = "4.26"
        pytorch_version = "1.13"
        python_version = "py39"

        ## Load Hugging Face Model
        huggingface_model = HuggingFaceModel(
            model_data=model_uri,
            role=execution_role_arn,
            transformers_version=transformers_version,
            pytorch_version=pytorch_version,
            py_version=python_version,
            env={"HF_TASK": "text-classification"},
        )

        output_s3_path = f"s3://{bucket}/outputs/inference/{job_id}"

        ## Create Transformer to run our batch job
        batch_job = huggingface_model.transformer(
            instance_count=instance_count,
            instance_type=instance_type,
            output_path=output_s3_path,
            strategy="SingleRecord",
        )

        ## Start Batch Transform job and uses s3 data as input
        batch_job.transform(
            job_name=f"sector-classification-transform-{job_id}",
            data=data_uri,
            content_type="application/json",
            split_type="Line",
            wait=False,
        )

        ## Copy inputs to ouputs folder for reference
        # copy data to outputs folder
        data_output_key = f"outputs/saved_data_input/{job_id}/data.csv"
        copy_file_new_destination(
            source_bucket=bucket,
            source_key=key,
            destination_bucket=bucket,
            destination_key=data_output_key,
        )

        # copy model config to outputs folder
        model_config_output_key = (
            f"outputs/saved_model_config/{job_id}/model_config.json"
        )
        copy_file_new_destination(
            source_bucket=bucket,
            source_key=model_config_key,
            destination_bucket=bucket,
            destination_key=model_config_output_key,
        )

        return {
            "statusCode": 200,
            "body": "Transform job initiated successfully",
            "data_uri": data_uri,
        }

    except Exception as e:
        msg_subject = "Error in Sector Classificaiton Batch Transform Lambda Function"
        send_sns_notification(topic_arn, str(e), msg_subject)

        return {
            "statusCode": 500,
            "body": json.dumps(f"Failed to initiate transform job: {str(e)}"),
        }
