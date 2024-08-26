
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
from generate_response import GenarateResponse
from generate_response import GenarateResponse
import os
import csv
# from get_pdf import download_pdfs_from_csv
import pandas as pd



def main():
    # html_url, pdf_filename = download_pdfs_from_csv()
    # print(pdf_filename)

    

    # df = pd.read_csv('../data/s1_lingo.csv')

    # for index, row in df.iterrows():
    html_url = "https://www.sec.gov/Archives/edgar/data/1943896/000119312524083525/d359771ds1.htm"
    pdf_name = "Rubrik"

    pdf_filename = os.path.join('../data', f'{pdf_name}.pdf')
    text = load_pdf(pdf_filename)

    html_texts = parse_html(html_url)

    # Ensure html_texts is a list of strings
    html_texts = [str(node) for node in html_texts]


    # Apply different chunking strategies
    fixed_chunks = fixed_size_chunking(text)
    semantic_chunks = semantic_chunking(text)
    agentic_chunks = agentic_chunking(text)

    char_chunks = character_text_splitting(" ".join(html_texts))
    sentence_chunks = sentence_splitting(" ".join(html_texts))
    semantic_chunks2 = semantic_splitting(" ".join(html_texts))

    # # Create vector stores for each chunking strategy
    fixed_vector_store = create_vector_store(fixed_chunks)
    semantic_vector_store = create_vector_store(semantic_chunks)
    agentic_vector_store = create_vector_store(agentic_chunks)
    
    char_vector_store = create_vector_store([chunk.page_content for chunk in char_chunks])
    sentence_vector_store = create_vector_store(sentence_chunks)
    semantic_vector_store2 = create_vector_store(semantic_chunks2)

    # Initialize RAG pipelines for each strategy
    fixed_rag_pipeline = RAGPipeline(fixed_vector_store)
    semantic_rag_pipeline = RAGPipeline(semantic_vector_store)
    agentic_rag_pipeline = RAGPipeline(agentic_vector_store)

    # Reset the vector store with new chunks for each strategy
    # fixed_rag_pipeline.reset_vector_store(fixed_chunks)
    # semantic_rag_pipeline.reset_vector_store(semantic_chunks)
    # agentic_rag_pipeline.reset_vector_store(agentic_chunks)

    char_rag_pipeline = RAGPipeline(char_vector_store)
    sentence_rag_pipeline = RAGPipeline(sentence_vector_store)
    semantic_rag_pipeline2 = RAGPipeline(semantic_vector_store2)

    # Example query for each strategy
    query = """
        You are a helpful assistant. I want you to find the lock up (lock-up) period as stated in the attached document.
        A lock-up period is a window of time when investors are not allowed to redeem or sell shares of a particular investment. 
        It usually lasts for around 180 days.
        Sometimes the starting date of the lock up period is explicitely stated in the document (e.g., 22 June 2021)
        and sometimes it is not very obvious. For example, you may find this line about the lock-up period: "..., ending on the date that is 180 days after the date of this prospectus". 
        In those cases the starting date of the lockup period is the date mentioned at the top of the document as a part of this sentence: "As filed with the Securities and Exchange Commission on {Date}"
    """
    # "from the date of this prospectus"
    # query = "what is the name of the company?"

    

    # Get the responses from different pipelines
    no_rag_pipeline = GenarateResponse().query(text, query)
    fixed_response = fixed_rag_pipeline.generate_response(query)
    semantic_response = semantic_rag_pipeline.generate_response(query)
    agentic_response = agentic_rag_pipeline.generate_response(query)
    char_response = char_rag_pipeline.generate_response(query)
    sentence_response = sentence_rag_pipeline.generate_response(query)
    semantic_split_response = semantic_rag_pipeline2.generate_response(query)

    # Define the data to be written to the CSV
    data = [
        ["No RAG Response", no_rag_pipeline],
        ["Fixed Size Chunking Response", fixed_response],
        ["Semantic Chunking Response", semantic_response],
        ["Agentic Chunking Response", agentic_response],
        ["Character Text Splitting Response", char_response],
        ["Sentence Splitting Response", sentence_response],
        ["Semantic Splitting Response", semantic_split_response]
    ]

    
    csv_file = f"{pdf_name}.csv"
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Chunking Method", "Response"])  # Write header
        writer.writerows(data)  # Write data

    print(f"Data saved to {csv_file}")


if __name__ == "__main__":
    main()
