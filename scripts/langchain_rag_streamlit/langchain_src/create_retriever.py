import os
import dotenv
from langchain.document_loaders.csv_loader import CSVLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

REVIEWS_CSV_PATH = "data/issuers_aggregated.csv"
REVIEWS_CHROMA_PATH = "chroma_data"

dotenv.load_dotenv()

loader = CSVLoader(file_path=REVIEWS_CSV_PATH)
data = loader.load()

documents = []
for row in data:
    document = " ".join(str(cell) for cell in row)
    documents.append(document)

def split_text_into_chunks(text, chunk_size):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

chunk_size = 1000
chunked_documents = []
for document in documents:
    chunks = split_text_into_chunks(document, chunk_size)
    chunked_document = " ".join(chunks)
    chunked_documents.append(chunked_document)

class Document:
    def __init__(self, content, metadata=None):
        self.page_content = content
        self.metadata = metadata if metadata is not None else {}

document_objects = [Document(content) for content in chunked_documents]

print("Creating Chroma database...")
reviews_vector_db = Chroma.from_documents(
    document_objects, OpenAIEmbeddings(), persist_directory=REVIEWS_CHROMA_PATH
)
print("Chroma database created.")
