import asyncio
import json
import sys
import uuid
from typing import Any, Dict, List, Optional

import spacy
import streamlit as st
from multi_agent_orchestrator.agents import (
    AgentCallbacks,
    AgentResponse,
    BedrockLLMAgent,
    BedrockLLMAgentOptions,
    ChainAgent,
    ChainAgentOptions,
    LambdaAgent,
    LambdaAgentOptions,
)
from multi_agent_orchestrator.orchestrator import (
    BedrockClassifier,
    BedrockClassifierOptions,
    MultiAgentOrchestrator,
    OrchestratorConfig,
)
from multi_agent_orchestrator.retrievers import (
    AmazonKnowledgeBasesRetriever,
    AmazonKnowledgeBasesRetrieverOptions,
)
from multi_agent_orchestrator.types import ConversationMessage, ParticipantRole

orchestrator = MultiAgentOrchestrator(
    options=OrchestratorConfig(
        LOG_AGENT_CHAT=True,
        LOG_CLASSIFIER_CHAT=True,
        LOG_CLASSIFIER_RAW_OUTPUT=True,
        LOG_CLASSIFIER_OUTPUT=True,
        LOG_EXECUTION_TIMES=True,
        MAX_RETRIES=3,
        USE_DEFAULT_AGENT_IF_NONE_IDENTIFIED=True,
        MAX_MESSAGE_PAIRS_PER_AGENT=10,
    ),
    classifier=BedrockClassifier(
        options=BedrockClassifierOptions(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0"  # default is anthropic.claude-3-5-sonnet-20240620-v1:0
        )
    ),
)


def input_payload_encoder(
    input_text: str,
    chat_history: List[ConversationMessage],
    user_id: str,
    session_id: str,
    additional_params: Optional[Dict[str, str]] = None,
) -> str:
    """Preprocesses input before sending to Lambda"""

    # Step 1: Load a pre-trained spaCy model (English model in this case)
    nlp = spacy.load("en_core_web_md")

    # Step 2: Define the NER function
    def extract_entities(text):
        # Process the input text with spaCy
        doc = nlp(text)

        # Extract entities and their labels
        entities = [ent.text for ent in doc.ents]

        return entities

    entities = extract_entities(input_text)

    return json.dumps(
        {
            "userQuestion": input_text,
            "entities": entities,
            "history": [message.__dict__ for message in chat_history],
            "user": user_id,
            "session": session_id,
            **(additional_params or {}),
        }
    )


def output_payload_decoder(response: Dict[str, Any]) -> ConversationMessage:
    """post processes output from Lambda"""

    decoded_response = json.loads(response["Payload"].read().decode("utf-8"))["body"]

    print("decoded_response", decoded_response)
    return ConversationMessage(
        role=ParticipantRole.ASSISTANT.value,
        content=[{"text": f"Response: {decoded_response}"}],
    )


options = LambdaAgentOptions(
    name="LambdaAgent",
    description="Retreives the price of a company's stock",
    function_name="arn:aws:lambda:us-west-2:597915789054:function:agent-bedrock-test",
    function_region="us-west-2",
    input_payload_encoder=input_payload_encoder,
    output_payload_decoder=output_payload_decoder,
)

lambda_agent = LambdaAgent(options)
# orchestrator.add_agent(lambda_agent)


agent2 = BedrockLLMAgent(
    BedrockLLMAgentOptions(
        name="Agent 2",
        description="Reads in a user question and response and provids a concise answer.",
        streaming=False,
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        inference_config={
            "temperature": 0.1,
        },
    )
)

chain_agent = ChainAgent(
    ChainAgentOptions(
        name="IntermediateChainAgent",
        description="Chain to retrieve the stock price of company and return a concise response",
        agents=[lambda_agent, agent2],
        default_output="The chain encountered an issue during processing.",
    )
)

orchestrator.add_agent(chain_agent)


retriever = AmazonKnowledgeBasesRetriever(
    AmazonKnowledgeBasesRetrieverOptions(
        knowledge_base_id="EQG6PLOV92",
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5,
                "overrideSearchType": "HYBRID",
            },
        },
    )
)

retriever_agent = BedrockLLMAgent(
    BedrockLLMAgentOptions(
        name="Forge Global FAQs",
        description="My personal agent is responsible for giving information related to Forge Global FAQs from a Knowledge Base for Amazon Bedrock.",
        streaming=False,
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        inference_config={
            "temperature": 0.1,
        },
        retriever=retriever,
        guardrail_config={
            "guardrailIdentifier": "wfn2yjhob5nw",
            "guardrailVersion": "2",
        },
    )
)

orchestrator.add_agent(retriever_agent)

web_retriever = AmazonKnowledgeBasesRetriever(
    AmazonKnowledgeBasesRetrieverOptions(
        knowledge_base_id="DFJ8PZA4TD",
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5,
                "overrideSearchType": "HYBRID",
            },
        },
    )
)

web_retriever_agent = BedrockLLMAgent(
    BedrockLLMAgentOptions(
        name="Forge Global Web Scraper",
        description="Agent uses a Knowledge Base to scrape company information from webpages on Forge Global",
        streaming=False,
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        inference_config={
            "temperature": 0.1,
        },
        retriever=web_retriever,
        guardrail_config={
            "guardrailIdentifier": "wfn2yjhob5nw",
            "guardrailVersion": "2",
        },
    )
)

orchestrator.add_agent(web_retriever_agent)


async def handle_request(
    _orchestrator: MultiAgentOrchestrator,
    _user_input: str,
    _user_id: str,
    _session_id: str,
):
    response: AgentResponse = await _orchestrator.route_request(
        _user_input, _user_id, _session_id
    )
    print("Response", response)
    # Print metadata
    print("\nMetadata:")
    print(f"Selected Agent: {response.metadata.agent_name}")
    if response.streaming:
        print("Response:", response.output.content[0]["text"])
    else:
        print("Response:", response.output.content[0]["text"])

    return response.output.content[0]["text"]


def run_streamlit(user_id, session_id):
    """Runs program in Streamlit (cmd: streamlit run app.py)"""

    st.header("Forge Assistant", divider="orange")  # Add Chat header
    if "messages" not in st.session_state.keys():  # Initialize the chat message history
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Ask me a question about the Forge or the private markets!",
            }
        ]

    if prompt := st.chat_input(
        "Your question"
    ):  # Prompt for user input and save to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

    for message in st.session_state.messages:  # Display the prior chat messages
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # If last message is not from assistant, generate a new response
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:

                    # Call the asynchronous function to get the chatbot's response
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    content = loop.run_until_complete(
                        handle_request(orchestrator, prompt, user_id, session_id)
                    )

                except:
                    content = "Sorry, I'm not able to answer your question."

                st.write(content)
                message = {"role": "assistant", "content": content}
                st.session_state.messages.append(
                    message
                )  # Add response to message history


def run_cmd_line_program(user_id, session_id):
    """Runs program in command line"""

    print("Welcome to the interactive Multi-Agent system. Type 'quit' to exit.")
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        if user_input.lower() == "quit":
            print("Exiting the program. Goodbye!")
            sys.exit()
        # Run the async function
        asyncio.run(handle_request(orchestrator, user_input, user_id, session_id))


if __name__ == "__main__":
    USER_ID = "user123"
    SESSION_ID = str(uuid.uuid4())

    run_cmd_line_program(USER_ID, SESSION_ID)

    # terminal cmd: steamlit run app.py
    # run_streamlit(USER_ID, SESSION_ID)
