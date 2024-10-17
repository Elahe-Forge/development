import os
import re

import streamlit as st
import weave
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI

memory = ChatMemoryBuffer.from_defaults(token_limit=1500)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.subheader(
    "Forge Guide? Chat Private Markets?  Forge Connect? Forge Whiz? Forge Genie?",
    divider="orange",
)  # Add Chat header

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "How can I help you?", "avatar": "🧑‍💼"}
    ]

# Initialize session state for Relevant links
if "links" not in st.session_state:
    st.session_state["links"] = [
        "Please visit [forgeglobal.com](www.forgeglobal.com) for more information"
    ]

# Initialize default suggestions in session state if not present
if "suggestions" not in st.session_state:
    st.session_state["suggestions"] = [
        "How do I register on Forge?",
        "How can I buy private market shares?",
        "Is there a minimum investment amount?",
    ]

if "input" not in st.session_state:
    st.session_state["input"] = ""  # Store input here


# Loading data locally into vector store
@st.cache_resource(show_spinner=True)
def index_data(data_path):

    data = SimpleDirectoryReader(input_dir=data_path).load_data()
    index = VectorStoreIndex.from_documents(data)

    return index


data_path = "./data/rag"
index = index_data(data_path)
llm = OpenAI(model="gpt-4o-mini")
memory = ChatMemoryBuffer.from_defaults(token_limit=500)
query_engine = index.as_query_engine(llm=llm)


@weave.op()
def extract_answer(chat_engine, prompt: str) -> dict:
    response = chat_engine.chat(prompt)
    return response


@weave.op()
def follow_up(query_engine, prompt: str) -> dict:
    response = query_engine.query(prompt)
    return response


# Process user input or suggestion click
def process_input(prompt):
    st.session_state["suggestions"] = []
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="🧑‍💼").write(prompt)

    # Initialize chat engine and get response
    chat_engine = index.as_chat_engine(
        chat_mode="context",
        memory=memory,
        system_prompt=(
            "You are a chat bot. Only provide answers based on FAQ's related to Forge Global. Do not use your general knowledge or make up any information. Do not say sorry, instead guide the user to possible solutions."
        ),
        verbose=False,
    )

    response = extract_answer(chat_engine, prompt)
    # Process and display assistant response
    msg = response.response.replace("$", r"\$")
    # Generate new suggestions based on the response
    suggestions_prompt = f"List 3 follow-up questions to ask based on the: \nPrompt - {prompt} \nResponse - {msg}"
    response_suggestions = follow_up(query_engine, suggestions_prompt)
    result = re.sub(r"^\d+\.\s*", "", response_suggestions.response, flags=re.MULTILINE)

    print(result)

    # Update the suggestions in session state
    st.session_state["suggestions"] = result.split("\n")

    # Generate call to action links
    link_prompt = f"Please provide at least 3 related links for the user to visit. For instance, Please go to www.forgeglobal.com to register, or contact your private market specialist at www.forgeglobal.com. If you include a website make sure it is a hyperlink, only return links and basic description: \nPrompt - {prompt} \nResponse - {msg}"
    response_links = follow_up(query_engine, link_prompt)
    links = re.sub(r"^\d+\.\s*", "", response_links.response, flags=re.MULTILINE)

    # Update the suggestions in session state
    st.session_state["links"] = links.split("\n")

    with st.chat_message("assistant"):
        st.write(msg)

    # Append assistant response to messages
    st.session_state["messages"].append({"role": "assistant", "content": msg})


# Create two separate containers
msg_container = st.container()
button_container = st.container()

# Display messages in the message container
with msg_container:
    for msg in st.session_state["messages"]:
        if msg["role"] == "assistant":
            st.chat_message(msg["role"], avatar="🤖").write(msg["content"])
        else:
            st.chat_message(msg["role"], avatar="🧑‍💼").write(msg["content"])

# Display the buttons in a separate container
with button_container:
    for idx, suggestion in enumerate(st.session_state["suggestions"][:2]):
        suggestion_button = st.button(suggestion, key=f"button_{idx}")
        if suggestion_button:
            process_input(suggestion)
            st.session_state["input"] = ""
            st.rerun()  # Use experimental_rerun to trigger rerun

# Input box to simulate user input
user_input = st.chat_input(placeholder="Ask me anything related to Forge...")
if user_input:
    del st.session_state["suggestions"]
    st.session_state["input"] = user_input
    process_input(user_input)
    st.session_state["input"] = ""  # Clear input after processing
    st.rerun()


with st.sidebar:
    st.subheader("Trusted Resources")
    for link in st.session_state["links"][:3]:
        st.write(link)
