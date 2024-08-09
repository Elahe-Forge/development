import ollama

class GenerateResponse:
    def __init__(self, text, model_name="llama3"):
        self.model_name = model_name
        self.text = text

    def query(self, query):
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": query 
                    + "\n\nContext:\n" + self.text,
                },
            ],
        )
        return response["message"]["content"]