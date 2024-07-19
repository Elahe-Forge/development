
from preprocess import load_pdf, parse_html
from chunking import (
    fixed_size_chunking, 
    semantic_chunking, 
    agentic_chunking,
    character_text_splitting,
    sentence_splitting,
    semantic_splitting
)
from vector_store import create_vector_store
from rag_pipeline import RAGPipeline
import os

def main():
    # Load PDF
#     text = load_pdf('data/reddit.pdf')

#     # Parse HTML from URL
#     html_url = 'https://www.utoronto.ca/'
#     html_texts = parse_html(html_url)

#     # Ensure html_texts is a list of strings
#     html_texts = [str(node) for node in html_texts]


#     # Apply different chunking strategies
#     fixed_chunks = fixed_size_chunking(text)
#     semantic_chunks = semantic_chunking(text)
#     agentic_chunks = agentic_chunking(text)

#     # char_chunks = character_text_splitting(" ".join(html_texts))
#     # sentence_chunks = sentence_splitting(" ".join(html_texts))
#     # semantic_chunks2 = semantic_splitting(" ".join(html_texts))

#     # Create vector stores for each chunking strategy
#     fixed_vector_store = create_vector_store(fixed_chunks)
#     semantic_vector_store = create_vector_store(semantic_chunks)
#     agentic_vector_store = create_vector_store(agentic_chunks)
    
#     # char_vector_store = create_vector_store([chunk.page_content for chunk in char_chunks])
#     # sentence_vector_store = create_vector_store(sentence_chunks)
#     # semantic_vector_store2 = create_vector_store(semantic_chunks2)

#     # Initialize RAG pipelines for each strategy
    fixed_rag_pipeline = RAGPipeline()
#     semantic_rag_pipeline = RAGPipeline(semantic_vector_store)
#     agentic_rag_pipeline = RAGPipeline(agentic_vector_store)

#     # char_rag_pipeline = RAGPipeline(char_vector_store)
#     # sentence_rag_pipeline = RAGPipeline(sentence_vector_store)
#     # semantic_rag_pipeline2 = RAGPipeline(semantic_vector_store2)

    # Example query for each strategy
    query = "what is capital of sweden."
    print("Fixed Size Chunking Response:")
    print(fixed_rag_pipeline.generate_response(query))
    
#     print("Semantic Chunking Response:")
#     print(semantic_rag_pipeline.generate_response(query))
    
#     print("Agentic Chunking Response:")
#     print(agentic_rag_pipeline.generate_response(query))

#     # print("Character Text Splitting Response:")
#     # print(char_rag_pipeline.generate_response(query))
    
#     # print("Sentence Splitting Response:")
#     # print(sentence_rag_pipeline.generate_response(query))
    
#     # print("Semantic Splitting Response:")
#     # print(semantic_rag_pipeline2.generate_response(query))

if __name__ == "__main__":
    main()
