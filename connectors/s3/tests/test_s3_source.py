import json
import unittest
from io import BytesIO
from typing import List
from unittest.mock import MagicMock

import pandas as pd

from connectors.s3.s3_source import S3Source


# Assuming S3Source is imported from your module


class TestS3Source(unittest.TestCase):

    def setUp(self):
        """Set up the mock S3 client and S3Source instance."""
        self.mock_s3_client = MagicMock()
        self.bucket_name = 'test-bucket'
        self.s3_source_df = S3Source[pd.DataFrame](self.bucket_name, s3_client=self.mock_s3_client)
        self.s3_source_list = S3Source[List](self.bucket_name, s3_client=self.mock_s3_client)

    def test_extract_csv(self):
        """Test extracting a CSV file from S3 and returning as a DataFrame."""
        csv_data = "col1,col2\n1,2\n3,4"
        self.mock_s3_client.get_object.return_value = {'Body': BytesIO(csv_data.encode())}

        df = self.s3_source_df.extract('data/file.csv')
        expected_df = pd.DataFrame({'col1': [1, 3], 'col2': [2, 4]})

        pd.testing.assert_frame_equal(df, expected_df)

    def test_extract_ndjson(self):
        """Test extracting NDJSON file and returning as a list of dicts."""
        ndjson_data = '{"col1": 1, "col2": 2}\n{"col1": 3, "col2": 4}'
        self.mock_s3_client.get_object.return_value = {'Body': BytesIO(ndjson_data.encode())}

        df = self.s3_source_df.extract('data/file.ndjson')
        expected_df = pd.DataFrame([{'col1': 1, 'col2': 2}, {'col1': 3, 'col2': 4}])

        pd.testing.assert_frame_equal(df, expected_df)

    def test_extract_json(self):
        """Test extracting a JSON file and returning as a list of dicts."""
        json_data = json.dumps([{"col1": 1, "col2": 2}, {"col1": 3, "col2": 4}])
        self.mock_s3_client.get_object.return_value = {'Body': BytesIO(json_data.encode())}

        data = self.s3_source_list.extract('data/file.json')
        expected_data = [{"col1": 1, "col2": 2}, {"col1": 3, "col2": 4}]

        self.assertEqual(data, expected_data)

    def test_extract_parquet(self):
        """Test extracting a Parquet file and returning as a DataFrame."""
        # Create a sample Parquet file in memory
        df_to_parquet = pd.DataFrame({'col1': [1, 3], 'col2': [2, 4]})
        buffer = BytesIO()
        df_to_parquet.to_parquet(buffer)
        buffer.seek(0)

        self.mock_s3_client.get_object.return_value = {'Body': buffer}

        df = self.s3_source_df.extract('data/file.parquet')
        pd.testing.assert_frame_equal(df, df_to_parquet)

    def test_list_keys(self):
        """Test listing keys in the S3 bucket."""
        self.mock_s3_client.get_paginator.return_value.paginate.return_value = [
            {'Contents': [{'Key': 'data/file1.csv'}, {'Key': 'data/file2.ndjson'}]}
        ]

        keys = self.s3_source_df.list('data/')
        expected_keys = ['data/file1.csv', 'data/file2.ndjson']

        self.assertEqual(keys, expected_keys)


if __name__ == '__main__':
    unittest.main()
