import json
from io import BytesIO
from typing import TypeVar, Generic, List, Union

import boto3
import pandas as pd
import pyarrow.parquet as pq

from connectors.source import Source

# Define the generic type variable T
T = TypeVar('T')


class S3Source(Source[T], Generic[T]):
    def __init__(self, bucket_name: str, s3_client=None):
        self.bucket_name = bucket_name
        self.s3_client = s3_client or boto3.client('s3')

    def _get_s3_object(self, key: str) -> bytes:
        """Helper method to retrieve raw data from S3."""
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read()

    def extract(self, key: str) -> T:
        """Extract data from S3 and return it as the specified type T."""
        raw_data = self._get_s3_object(key)

        # Infer file format based on file extension
        if key.endswith('.csv'):
            return self._process_extraction(raw_data, 'csv')
        elif key.endswith('.ndjson'):
            return self._process_extraction(raw_data, 'ndjson')
        elif key.endswith('.json'):
            return self._process_extraction(raw_data, 'json')
        elif key.endswith('.parquet'):
            return self._process_extraction(raw_data, 'parquet')
        else:
            raise ValueError(f"Unsupported file type for key: {key}")

    def _process_extraction(self, raw_data: bytes, file_format: str) -> T:
        """Process the raw data based on the file format and return it as type T."""
        if file_format == 'csv':
            df = pd.read_csv(BytesIO(raw_data))
            return self._convert_output(df)

        elif file_format == 'ndjson':
            df = pd.read_json(BytesIO(raw_data), lines=True)
            return self._convert_output(df)

        elif file_format == 'json':
            data = json.loads(raw_data.decode('utf-8'))
            return self._convert_output(data)

        elif file_format == 'parquet':
            df = pq.read_table(BytesIO(raw_data)).to_pandas()
            return self._convert_output(df)

    @staticmethod
    def _convert_output(data: Union[pd.DataFrame, List[dict], dict]) -> T:
        """Convert the extracted data into the desired return type T."""
        if isinstance(data, pd.DataFrame):
            return data  # Assume T is pd.DataFrame and return directly

        elif isinstance(data, (list, dict)):
            return data  # Assume T is list or dict and return directly

        raise TypeError(f"Unsupported return type for data: {type(data)}")

    def list(self, prefix: str = '') -> List[str]:
        """List all keys in the S3 bucket or within a specific folder (prefix)."""
        keys = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if 'Contents' in page:
                keys.extend([content['Key'] for content in page['Contents']])
        return keys
