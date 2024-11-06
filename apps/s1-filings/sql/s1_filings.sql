
-- CREATE DATABASE data_science;
DATABASE source

CREATE SCHEMA s1_filings;

CREATE TABLE IF NOT EXISTS s1_filings.data_ops_fields_extraction (
id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
accession_number VARCHAR(50) NOT NULL UNIQUE,
company_name TEXT NOT NULL,
cik VARCHAR(10) NOT NULL,
url TEXT NOT NULL,
published_datetime TIMESTAMPTZ,
form_type VARCHAR(10) NOT NULL,
s3_file_path TEXT NOT NULL,
date_filed DATE NOT NULL,
created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

select * from s1_filings.data_ops_fields_extraction;