import json
import unittest
from io import BytesIO

import boto3
import pandas as pd
from moto import mock_aws

from connectors.s3.s3_sink import S3Sink

class TestS3Sink(unittest.TestCase):

    # @mock_aws
    def setUp(self):
        """Set up mock S3 environment and initialize the S3Sink."""
        self.mock_aws = mock_aws()
        self.mock_aws.start()

        self.bucket_name = 'test-bucket'
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        self.sink = S3Sink(bucket_name=self.bucket_name, s3_client=self.s3_client)

    def tearDown(self):
        self.mock_aws.stop()

    def _get_s3_object_content(self, key: str):
        """Helper method to retrieve object content from S3."""
        obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return obj['Body'].read().decode('utf-8')

    def test_upload_csv(self):
        """Test uploading a CSV file."""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        key = 'test.csv'
        self.sink.load(df, key)

        # Check if the CSV was uploaded
        content = self._get_s3_object_content(key)
        self.assertIn('col1,col2', content)
        self.assertIn('1,a', content)

    def test_upload_json_list(self):
        """Test uploading a JSON file (list format)."""
        data = [{'col1': 1, 'col2': 'a'}, {'col1': 2, 'col2': 'b'}]
        key = 'test.json'
        self.sink.load(data, key)

        # Check if the JSON was uploaded
        content = self._get_s3_object_content(key)
        self.assertEqual(json.loads(content), data)

    def test_upload_json_dict(self):
        """Test uploading a JSON file (dict format)."""
        data = {'col1': 1, 'col2': 'a'}
        key = 'test.json'
        self.sink.load(data, key)

        # Check if the JSON was uploaded
        content = self._get_s3_object_content(key)
        self.assertEqual(json.loads(content), data)

    def test_upload_ndjson(self):
        """Test uploading an NDJSON file."""
        data = [{'col1': 1, 'col2': 'a'}, {'col1': 2, 'col2': 'b'}]
        key = 'test.ndjson'
        self.sink.load(data, key)

        # Check if the NDJSON was uploaded
        content = self._get_s3_object_content(key)
        lines = content.splitlines()
        self.assertEqual(json.loads(lines[0]), data[0])
        self.assertEqual(json.loads(lines[1]), data[1])

    def test_upload_parquet(self):
        """Test uploading a Parquet file."""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        key = 'test.parquet'
        self.sink.load(df, key)

        # Check if the Parquet file was uploaded
        obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        parquet_data = BytesIO(obj['Body'].read())
        loaded_df = pd.read_parquet(parquet_data)
        pd.testing.assert_frame_equal(df, loaded_df)


if __name__ == '__main__':
    unittest.main()
