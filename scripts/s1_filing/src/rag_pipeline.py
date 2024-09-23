import ollama
from vector_store import create_vector_store

# from langchain.prompts import PromptTemplate
# from langchain_community.chat_models import ChatOpenAI
# from langchain.text_splitter import RecursiveCharacterTextSplitter 
# from langchain.embeddings import BedrockEmbeddings
# from langchain.vectorstores import FAISS
# from langchain.chains import RetrievalQA
# from langchain.prompts import PromptTemplate
# from langchain.llms import Bedrock
# import boto3

class RAGPipeline:
    def __init__(self, vector_store, model_name="llama3"):
        self.vector_store = vector_store
        self.model_name = model_name
        # self.processed_data = None

    def generate_response(self, query):
        # if self.processed_data is None:
        #     self.preprocess_data()
        

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

        # openai_llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key="")

        # template = """
        #     Answer the question as truthfully as possible strictly using only the provided text, and if the answer is not contained within the text, say "I don't know". Skip any preamble text and reasoning and give just the answer.

        #     <text>{context}</text>
        #     <question>{question}</question>
        #     <answer>"""

        # qa_prompt = PromptTemplate(template=template, input_variables=["context", "question"])

        # # Combine the prompt and the question with the document context
        # prompt_with_context = qa_prompt.format(context=context, question=query)

        # result = openai_llm.predict(prompt_with_context)

        # return result


        # bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
        # qa_prompt = PromptTemplate(template=template, input_variables=["context","question"])

        # chain_type_kwargs = { "prompt": qa_prompt, "verbose": False } # change verbose to True if you need to see what's happening

        # bedrock_llm = Bedrock(client=bedrock, model_id="anthropic.claude-v2")
        # qa = RetrievalQA.from_chain_type(
        #     llm=bedrock_llm, 
        #     chain_type="stuff", 
        #     retriever=context,
        #     chain_type_kwargs=chain_type_kwargs,
        #     verbose=False # change verbose to True if you need to see what's happening
        # )
        # result = qa.run(query)
        # return result

    
    def reset_vector_store(self, new_chunks):
        self.vector_store = create_vector_store(new_chunks)



    # def preprocess_data(self):
    #     """
    #     Preprocess the data (chunking, indexing, etc.) only once.
    #     """
    #     if self.processed_data is None:
    #         self.processed_data = self.vector_store.process_all_documents()
    
