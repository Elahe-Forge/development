from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, load_index_from_storage, StorageContext
# from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
import os.path
import os
from dotenv import load_dotenv


load_dotenv()
model = os.getenv('OLLAMA_EMBEDDINGS_MODEL')
base_url = os.getenv('OLLAMA_EMBEDDINGS_URL')


if os.getenv('LLM_PROVIDER') == "ollama":
    Settings.embed_model = OllamaEmbedding(
        model_name=model,
        base_url=base_url, # 35 runs CPU only
        ollama_additional_kwargs={"mirostat": 0},
)
    
if os.getenv('LLM_PROVIDER') == "bedrock":
    raise Exception("bedrock not yet implemented")




# check if storage already exists
PERSIST_DIR = "./storage"

def get_index():
    if not os.path.exists(PERSIST_DIR):
        # load the documents and create the index
        documents = SimpleDirectoryReader("data").load_data()
        index = VectorStoreIndex.from_documents(documents)
        # store it for later
        index.storage_context.persist(persist_dir=PERSIST_DIR)
    else:
        # load the existing index
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        index = load_index_from_storage(storage_context)
    return index