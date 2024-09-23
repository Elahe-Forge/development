import ollama

from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI

class NoRagResponse:
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
    
    def query_gpt(self, text, query):

        openai_llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key="")

        template = """
            Answer the question as truthfully as possible strictly using only the provided text, and if the answer is not contained within the text, say "I don't know". Skip any preamble text and reasoning and give just the answer.

            <text>{context}</text>
            <question>{question}</question>
            <answer>"""

        qa_prompt = PromptTemplate(template=template, input_variables=["context", "question"])

        # Combine the prompt and the question with the document context
        prompt_with_context = qa_prompt.format(context=text, question=query)

        # Run the LLM with the full prompt
        result = openai_llm.generate([{"role": "system", "content": prompt_with_context}])

        return result
    
    # def query_claude(self, text, query):
    #     bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
    #     template = """
    #         Answer the question as truthfully as possible strictly using only the provided text, and if the answer is not contained within the text, say "I don't know". Skip any preamble text and reasoning and give just the answer.

    #         <text>{context}</text>
    #         <question>{question}</question>
    #         <answer>"""

    #     qa_prompt = PromptTemplate(template=template, input_variables=["context","question"])

    #     chain_type_kwargs = { "prompt": qa_prompt, "verbose": False } # change verbose to True if you need to see what's happening

    #     bedrock_llm = Bedrock(client=bedrock, model_id="anthropic.claude-v2")
    #     prompt_with_context = qa_prompt.format(context=text, question=query)
    #     result = qa.run(query)
    #     return result

