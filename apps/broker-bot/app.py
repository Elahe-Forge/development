import os
import time

import streamlit as st
import weave
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI

memory = ChatMemoryBuffer.from_defaults(token_limit=1500)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.header("Broker Bot", divider="rainbow")  # Add Chat header
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "How can I help you?"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


@st.cache_resource(show_spinner=True)
def index_data(data_path):

    data = SimpleDirectoryReader(input_dir=data_path).load_data()
    index = VectorStoreIndex.from_documents(data)

    return index


data_path = "./data/"
index = index_data(data_path)

llm = OpenAI(model="gpt-4o-mini")

memory = ChatMemoryBuffer.from_defaults(token_limit=1500)


def get_chat_engine(chat_mode):
    if chat_mode == "best":
        chat_engine = index.as_chat_engine(chat_mode="best", llm=llm, verbose=False)
    if chat_mode == "context":
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            memory=memory,
            system_prompt=(
                "You are a chat bot. Only provide answers based on FAQ's related to Forge Global. Do not use your general knowledge."
                "After providing your response, please make actionable suggestions if appropriate. For instance, Please go to forgeglobal.com to register, or contact your private market specialist at forgeglobal.com"
            ),
            verbose=False,
        )
    return chat_engine


@weave.op()
def extract_answer(chat_engine, prompt: str) -> dict:
    response = chat_engine.chat(prompt)
    return response


chat_mode = "context"


# Streamed response emulator
def response_generator(msg):
    for word in msg.split():
        yield word + " "
        time.sleep(0.05)


if prompt := st.chat_input():

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    weave.init("broker-bot-v0")
    chat_engine = get_chat_engine(chat_mode)
    response = extract_answer(chat_engine, prompt)

    msg = response.response.replace("$", r"\$")

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        # st.write_stream(response_generator(msg))
        st.write(msg)

    st.session_state.messages.append({"role": "assistant", "content": msg})
    # st.chat_message("assistant").write(msg)
