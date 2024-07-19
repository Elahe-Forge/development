
import fitz  
import requests
from bs4 import BeautifulSoup
from llama_index.core import Document
from llama_index.core.node_parser import HTMLNodeParser

def load_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def parse_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        html_doc = response.text
        document = Document(id_=url, text=html_doc)

        parser = HTMLNodeParser(tags=["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section"])
        nodes = parser.get_nodes_from_documents([document])
        return nodes
    else:
        print("Failed to fetch HTML content:", response.status_code)
        return []
    
