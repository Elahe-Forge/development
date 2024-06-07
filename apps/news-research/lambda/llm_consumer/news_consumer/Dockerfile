FROM public.ecr.aws/lambda/python:3.11


WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the main Lambda function requirements and install them
COPY lambda/llm_consumer/news_consumer/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy the shared utility llm_handler.py from the llm_handler directory
COPY llm_lib/llm_handler/llm_handler.py .
COPY llm_lib/llm_handler/requirements.txt .
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt


# Copy the Lambda function code
# This path must be relative to the context now set at the project root
COPY lambda/llm_consumer/news_consumer/lambda_function.py .

CMD ["lambda_function.handler"]
