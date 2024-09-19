import json

import boto3


def load_and_save_config(bucket_name: str, file_key: str, job_id: int) -> dict:

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

        copy_source = {"Bucket": bucket_name, "Key": file_key}
        destination_key = f"outputs/saved_input_config/config_{job_id}.json"

        s3.copy(copy_source, bucket_name, destination_key)
        print(f"JSON file copied to destination: s3://{bucket_name}/{destination_key}")

        return config_data
    except Exception as e:
        print(f"Error handling JSON file: {e}")


def load_model_parameters(config_data: dict, bucket: str, job_id: int) -> dict:
    try:
        # default values
        model_name = "distilbert-base-uncased"
        epochs = 1
        train_batch_size = 8
        learning_rate = 5e-5
        weight_decay = 0
        experiment_name = f"sector-classification-experiments-v1"
        train_input_path = (
            "s3://team-orange-datasets/sector-subsector-classification-alden-curated/train/",
        )
        test_input_path = "s3://team-orange-datasets/sector-subsector-classification-alden-curated/test/"
        transformers_version = "4.26"
        pytorch_version = "1.13"
        python_version = "py39"
        instance_type = "ml.g4dn.xlarge"
        instance_count = 1

        model_parameters = {
            "job_id": job_id,
            "epochs": epochs,
            "train_batch_size": train_batch_size,
            "model_name": model_name,
            "weight_decay": weight_decay,
            "learning_rate": learning_rate,
            "train_input_path": train_input_path,
            "test_input_path": test_input_path,
            "instance_type": instance_type,
            "instance_count": instance_count,
            "transformers_version": transformers_version,
            "pytorch_version": pytorch_version,
            "python_version": python_version,
            "experiment_name": experiment_name,
        }

        # update model_parameters if item in config data
        for k, v in model_parameters.items():
            if k in config_data:
                model_parameters[k] = config_data[k]

        model_parameters["code_location"] = f"s3://{bucket}/outputs/code_location/"
        model_parameters["output_path"] = f"s3://{bucket}/outputs/model_output/"
        model_parameters["job_name"] = (
            f"sector-classification-{model_parameters['model_name']}-{job_id}"
        )
        model_parameters["model_output_path"] = (
            f"{model_parameters['output_path']}{model_parameters['job_name']}/output/model.tar.gz"
        )

        return model_parameters
    except Exception as e:
        print(f"ERROR occurred when loading model parameters: {e}")
