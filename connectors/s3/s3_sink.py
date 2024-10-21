from typing import TypeVar

T = TypeVar('T')

import json
from io import BytesIO
from typing import TypeVar, Generic, List, Union

import boto3
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa

from connectors.sink import Sink

T = TypeVar('T')


class S3Sink(Sink[T], Generic[T]):
    def __init__(self, bucket_name: str, s3_client=None):
        self.bucket_name = bucket_name
        self.s3_client = s3_client or boto3.client('s3')

    def load(self, data: T, key: str):
        """Upload data to S3 based on the file extension."""
        if key.endswith('.csv'):
            self._process_loading(data, 'csv', key)
        elif key.endswith('.ndjson'):
            self._process_loading(data, 'ndjson', key)
        elif key.endswith('.json'):
            self._process_loading(data, 'json', key)
        elif key.endswith('.parquet'):
            self._process_loading(data, 'parquet', key)
        else:
            raise ValueError(f"Unsupported file type for key: {key}")

    def _process_loading(self, data: T, file_format: str, key: str):
        """Process the data based on its format and upload it to S3."""
        if file_format == 'csv' and isinstance(data, pd.DataFrame):
            self._upload_csv(data, key)
        elif file_format == 'ndjson' and isinstance(data, list):
            self._upload_ndjson(data, key)
        elif file_format == 'json' and isinstance(data, (list, dict)):
            self._upload_json(data, key)
        elif file_format == 'parquet' and isinstance(data, pd.DataFrame):
            self._upload_parquet(data, key)
        else:
            raise TypeError(f"Unsupported data type for {file_format}: {type(data)}")

    def _upload_csv(self, data: pd.DataFrame, key: str):
        """Upload a Pandas DataFrame as a CSV to S3."""
        csv_buffer = BytesIO()
        data.to_csv(csv_buffer, index=False)
        self._upload_to_s3(csv_buffer.getvalue(), key, 'text/csv')

    def _upload_ndjson(self, data: List[dict], key: str):
        """Upload a list of dicts as an NDJSON file to S3."""
        ndjson_buffer = BytesIO("\n".join(json.dumps(record) for record in data).encode('utf-8'))
        self._upload_to_s3(ndjson_buffer.getvalue(), key, 'application/x-ndjson')

    def _upload_json(self, data: Union[list, dict], key: str):
        """Upload JSON data to S3."""
        json_buffer = BytesIO(json.dumps(data).encode('utf-8'))
        self._upload_to_s3(json_buffer.getvalue(), key, 'application/json')

    def _upload_parquet(self, data: pd.DataFrame, key: str):
        """Upload a Pandas DataFrame as a Parquet file to S3."""
        parquet_buffer = BytesIO()
        # Create a PyArrow Table from the Pandas DataFrame
        table = pa.Table.from_pandas(df=data)
        # Write the table to the Parquet buffer
        pq.write_table(table, parquet_buffer)
        # Upload the buffer to S3
        parquet_buffer.seek(0)  # Rewind the buffer before reading it
        self._upload_to_s3(parquet_buffer.getvalue(), key, 'application/octet-stream')

    def _upload_to_s3(self, body: bytes, key: str, content_type: str):
        """Helper method to upload raw data to S3."""
        self.s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=body, ContentType=content_type)
