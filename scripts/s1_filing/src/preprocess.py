
import fitz  
import requests
from bs4 import BeautifulSoup
from llama_index.core import Document
from llama_index.core.node_parser import HTMLNodeParser
import re

def load_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    
    return text

def parse_html(url):

    headers = {'User-Agent': 'ela, elahe.paikari@forgeglobal.com'}
    response = requests.get(url, headers=headers)
    
    # if response.status_code == 200:
    #     html_doc = response.text
    #     document = Document(id_=url, text=html_doc)


    #     parser = HTMLNodeParser(tags=["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section"])
    #     nodes = parser.get_nodes_from_documents([document])
    #     return nodes
    # else:
    #     print("Failed to fetch HTML content:", response.status_code)
    #     return []
    if response.status_code == 200:
        html_doc = response.text
        document = Document(id_=url, text=html_doc)
        
        # Debug: Check if document text is not empty
        # print(f"Document Text Length: {len(html_doc)}")

        # # Using BeautifulSoup to inspect the document structure
        # soup = BeautifulSoup(html_doc, 'html.parser')
        # print(f"Title of Document: {soup.title.string if soup.title else 'No title'}")
        
        # Find and print elements in the document (for inspection)
        # for tag in ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section", "div", "span"]:
        #     elements = soup.find_all(tag)
        #     if elements:
        #         print(f"Found elements in tag: {tag}")
        #         for element in elements[:1]:  # Print first 5 elements of each tag
        #             print(element.get_text(strip=True))

        # Use the HTMLNodeParser to get nodes
        parser = HTMLNodeParser(tags=["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section", "div", "span"])
        nodes = parser.get_nodes_from_documents([document])
        # print(f"Total nodes found: {len(nodes)}")
        # if nodes:
        #     for node in nodes[:1]:  # Print the first 5 nodes for inspection
        #         print(f"Node content: {node.text}")
        # #     print("yes")

        # Return nodes or inspect them further
        return nodes
    else:
        print("Failed to fetch HTML content:", response.status_code)
        return []
    
def clean_text(text):
    pattern = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),?\s*\d{1,2}:\d{2}\s*[APM]*"

    cleaned_text = re.sub(pattern, '', text)
    return cleaned_text

    
