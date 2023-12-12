#!/bin/bash

LAMBDA_SCRIPT="child_lambda_function.py"
OUTPUT_ZIP="build.zip"

# Directory containing lambda function
LAMBDA_DIR="lambda/serp_api_producer"

# Path to the virtual environment's site-packages
VENV_SITE_PACKAGES=".env/lib/python3.9/site-packages/"

# Activate the virtual environment
source .env/bin/activate

# Install dependencies (if requirements.txt is present)
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Navigate to the site-packages directory
cd $VENV_SITE_PACKAGES

# Zip the contents of site-packages
zip -r9 ${OLDPWD}/${OUTPUT_ZIP} .

# Navigate back to the original directory and add the Lambda function script to the zip
cd -
cd $LAMBDA_DIR
zip -g ${OLDPWD}/${OUTPUT_ZIP} $LAMBDA_SCRIPT

cd -

echo "Lambda function packaged into $OUTPUT_ZIP"
