import ollama
from vector_store import create_vector_store

class RAGPipeline:
    def __init__(self, vector_store, model_name="llama3"):
        self.vector_store = vector_store
        self.model_name = model_name
        # self.processed_data = None

    def generate_response(self, query):
        # if self.processed_data is None:
        #     self.preprocess_data()
        

        retrieved_docs = self.vector_store.search(query, top_k=5)
        context = " ".join(retrieved_docs)
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": query 
                    + "\n\nContext:\n" + context,
                },
            ],
        )
        return response["message"]["content"]
    
    def reset_vector_store(self, new_chunks):
        self.vector_store = create_vector_store(new_chunks)



    # def preprocess_data(self):
    #     """
    #     Preprocess the data (chunking, indexing, etc.) only once.
    #     """
    #     if self.processed_data is None:
    #         self.processed_data = self.vector_store.process_all_documents()
    
