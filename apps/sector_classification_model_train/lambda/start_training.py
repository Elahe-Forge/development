import json
import os
import time

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from sagemaker.experiments import Run
from sagemaker.huggingface import HuggingFace
from sagemaker.session import Session
from smexperiments.experiment import Experiment
from utils.utils import load_and_save_config, load_model_parameters


def handler(event, context):
    print("event", event)
    try:
        load_dotenv()

        region = "us-west-2"
        sess = boto3.Session(region_name=region)
        sm = sess.client("sagemaker")
        # role = os.getenv("SAGEMAKER_ROLE")

        execution_role_arn = os.getenv("TARGET_ROLE_ARN")
        if not execution_role_arn:
            raise ValueError("Execution role ARN not set in environment variables")

        print(f"Execution Role ARN: {execution_role_arn}")
        # role = "arn:aws:iam::597915789054:role/brandtbo-sagemaker-train"

        if "test" in event:
            bucket = event["bucket"]
            key = event["key"]
        else:
            bucket = event["Records"][0]["s3"]["bucket"]["name"]
            key = event["Records"][0]["s3"]["object"]["key"]

        print("bucket", bucket)
        print("key", key)

        job_id = int(time.time())
        # read in config file
        config_data = load_and_save_config(bucket, key, job_id)

        model_parameters = load_model_parameters(config_data, bucket, job_id)

        try:
            sector_class_experiment = Experiment.create(
                experiment_name=model_parameters["experiment_name"],
                sagemaker_boto_client=sm,
            )
            print("Created experiment:", sector_class_experiment.experiment_name)

        except:
            print("Experiment already exists:", model_parameters["experiment_name"])

        print(model_parameters["experiment_name"])

        with Run(
            experiment_name=model_parameters["experiment_name"],
            sagemaker_session=Session(),
            run_name=f"{model_parameters['model_name'].split('-')[0]}-epoch-{model_parameters['epochs']}-{job_id}",
        ) as run:

            print("huggingface_estimator")
            # HuggingFace container in SageMaker
            huggingface_estimator = HuggingFace(
                entry_point="train.py",
                source_dir="./scripts",  # reads requirements.txt file in scripts directory
                instance_type=model_parameters["instance_type"],
                instance_count=model_parameters["instance_count"],
                role=execution_role_arn,
                transformers_version=model_parameters["transformers_version"],
                pytorch_version=model_parameters["pytorch_version"],
                py_version=model_parameters["python_version"],
                hyperparameters=model_parameters,
                enable_sagemaker_metrics=True,
                code_location=model_parameters["code_location"],
                output_path=model_parameters["output_path"],
            )

            print("huggingface_estimator.fit")
            # starts training job in SageMaker

            huggingface_estimator.fit(
                inputs={
                    "train": model_parameters["train_input_path"],
                    "test": model_parameters["test_input_path"],
                },
                job_name=model_parameters["job_name"],
                wait=False,
            )

            return {"statusCode": 200, "body": "Model Training Started"}

    except ClientError as e:
        response = {
            "statusCode": 500,
            "body": json.dumps(
                {"error": str(e), "message": e.response["Error"]["Message"]}
            ),
        }
        return response
