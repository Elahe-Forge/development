import ollama

class RAGPipeline:
    # def __init__(self, vector_store, model_name="llama3"):
    def __init__(self, model_name="llama3"):
        # self.vector_store = vector_store
        self.model_name = model_name

    def generate_response(self, query):
        # retrieved_docs = self.vector_store.search(query, top_k=5)
        # context = " ".join(retrieved_docs)
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": query 
                    # + "\n\nContext:\n" + context,
                },
            ],
        )
        return response["message"]["content"]
