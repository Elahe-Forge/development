FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY src/ src/
COPY data/ data/
# COPY tests/ tests/

# COPY src/test_connection.py src/test_connection.py

CMD ["python", "src/main.py"]
