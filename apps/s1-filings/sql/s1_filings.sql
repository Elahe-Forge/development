
CREATE DATABASE data_science;

CREATE SCHEMA s1_filings;

CREATE TABLE s1_filings.data_ops_fields_extraction (
accession_number VARCHAR(50) PRIMARY KEY,
company_name TEXT,
cik VARCHAR(10),
url TEXT,
published_datetime TIMESTAMPTZ, 
form_type VARCHAR(10),
s3_file_path TEXT,
filed_date DATE
);

select * from s1_filings.data_ops_fields_extraction;