from typing import Optional, List, Generator
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from pydantic import BaseModel
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

class SnowflakeCredentials(BaseModel):
    """Snowflake credentials model."""

    account: str
    user: str
    private_key: str
    private_key_passphrase: Optional[str] = None
    warehouse: str
    database: str
    db_schema: str


class SnowflakeClient:
    """Snowflake client.
    Args:
        snowflake_credentials (SnowflakeCredentials): Snowflake credentials.
    """

    def __init__(self, creds: SnowflakeCredentials):
        """Initialize the Snowflake client."""
        private_key = self._load_private_key_from_string(
            private_key_str=f"-----BEGIN PRIVATE KEY-----\n{creds.private_key}\n-----END PRIVATE KEY-----",  # noqa: E501
            passphrase=None,
        )
        self.database = creds.database
        self.schema = creds.db_schema
        self.snowflake_url = URL(
            account=creds.account,
            user=creds.user,
            warehouse=creds.warehouse,
            database=creds.database,
            schema=creds.db_schema,
        )

        self.engine = create_engine(
            self.snowflake_url,
            connect_args={
                "private_key": private_key,
            },
        )
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        # self.metadata = MetaData(bind=self.engine)

    @staticmethod
    def _load_private_key_from_string(
        private_key_str: str, passphrase: Optional[str]
    ):
        """Load the private key from a string."""
        private_key = serialization.load_pem_private_key(
            data=private_key_str.encode(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend(),
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def fetchall(self, query: str) -> list:
        """Fetch all rows from the query."""
        result = self.session.execute(text(query))
        return result.fetchall()

    def fetch_batch(
        self, query: str, batch_size: int = 1000
    ) -> Generator[List, None, None]:
        """Fetch rows in batches from the query."""
        result = self.session.execute(text(query))
        while True:
            rows = result.fetchmany(size=batch_size)
            if not rows:
                break
            yield rows

    def merge(
        self,
        df: pd.DataFrame,
        temp_table_name: str,
        target_table_name: str,
        merge_query: str,
    ):
        """Merge a DataFrame into a target table using a merge query.

        Args:
            df (pd.DataFrame): DataFrame to merge.
            temp_table_name (str): Name of the temporary table.
            merge_query (str): Customized merge SQL query.
        """
        drop_temp_table_query = f"DROP TABLE IF EXISTS {temp_table_name}"
        self.session.execute(text(drop_temp_table_query))
        self.session.commit()

        create_temp_table_query = f"""
            CREATE TEMPORARY TABLE {temp_table_name}
            LIKE {target_table_name}
        """
        self.session.execute(text(create_temp_table_query))
        self.session.commit()

        # Load the DataFrame to a temporary table
        df.to_sql(
            temp_table_name,
            self.engine,
            if_exists="append",
            index=False,
            schema=self.schema,
        )

        self.session.execute(text(merge_query))
        self.session.commit()
        self.session.execute(text(drop_temp_table_query))


    def close(self):
        """Close the session."""
        self.session.close()