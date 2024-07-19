import nltk
from langchain.text_splitter import CharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Document
import os

# nltk.download('punkt')
# from nltk.tokenize import sent_tokenize

# Fixed Size Chunking
def fixed_size_chunking(text, chunk_size=500, chunk_overlap=0, separator=""):
    splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separator=separator)
    chunks = splitter.split_text(text)
    return chunks

# Semantic Chunking
def semantic_chunking(text, max_sentences=3):
    splitter = SentenceSplitter()
    sentences = splitter.split_text(text)
    
    # Group sentences into groups of max_sentences
    grouped_sentences = [" ".join(sentences[i:i + max_sentences]) for i in range(0, len(sentences), max_sentences)]
    
    return grouped_sentences

# Agentic Chunking
def agentic_chunking(text):
    splitter = SentenceSplitter()
    propositions = splitter.split_text(text)  # Simplified: consider each sentence a proposition
    
    agentic_chunks = []
    current_chunk = ""
    for proposition in propositions:
        if len(current_chunk) + len(proposition) < 500:  # Assuming max chunk size of 500
            current_chunk += " " + proposition
        else:
            agentic_chunks.append(current_chunk.strip())
            current_chunk = proposition
    if current_chunk:
        agentic_chunks.append(current_chunk.strip())
    
    return agentic_chunks

# Character Text Splitting
def character_text_splitting(text):
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    texts = text_splitter.create_documents([text])
    return texts

# Sentence Splitting
def sentence_splitting(text):
    splitter = SentenceSplitter(
        chunk_size=1024,
        chunk_overlap=20,
    )
    document = Document(id_="text", text=text)
    nodes = splitter.get_nodes_from_documents([document])
    return [node.text for node in nodes]

# Semantic Splitting
def semantic_splitting(text):
    os.environ["OPENAI_API_KEY"] = ""
    embed_model = OpenAIEmbedding()
    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model
    )
    document = Document(id_="text", text=text)
    nodes = splitter.get_nodes_from_documents([document])
    return [node.text for node in nodes]

# Semantic Chunking with Langchain
def semantic_chunking_with_langchain(text):
    os.environ["OPENAI_API_KEY"] = ""
    embeddings = OpenAIEmbeddings()
    chunker = SemanticChunker(embeddings)
    chunks = chunker.create_documents([text])
    return chunks
