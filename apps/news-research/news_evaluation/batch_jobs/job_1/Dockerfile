FROM public.ecr.aws/docker/library/python:3.12

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/
# COPY selfcheckgpt /app/selfcheckgpt

# Upgrade pip and install the specified packages
# RUN pip install --upgrade pip
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Clone the selfcheckgpt repository and install it
RUN git clone https://github.com/potsawee/selfcheckgpt.git /app/selfcheckgpt \
    && cd /app/selfcheckgpt \
    && pip install .

# Copy the batch job script into the container at /app
COPY job_1_script.py /app/

# Define the command to run when the container starts
CMD ["python", "job_1_script.py"]
