import ollama

class GenarateResponse:
    def __init__(self, model_name="llama3"):
        self.model_name = model_name

    def query(self, text, query):
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": query 
                    + "\n\nContext:\n" + text,
                },
            ],
        )
        return response["message"]["content"]
