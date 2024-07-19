import ollama
import chromadb
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, dimension=768, embedding_model='mxbai-embed-large'):
        self.dimension = dimension
        self.embedding_model = embedding_model
        self.client = chromadb.Client()
        try:
            self.collection = self.client.create_collection(name="documents")
        except chromadb.db.base.UniqueConstraintError:
            self.collection = self.client.get_collection(name="documents")
            logger.info("Using existing collection: documents")

    def add_documents(self, texts):
        for i, text in enumerate(texts):
            embedding = self.embed_text(text)
            self.collection.add(
                ids=[str(i)],
                embeddings=[embedding],
                documents=[text]
            )
            logger.info(f"Embedding added for text: {text[:50]}...")

    def embed_text(self, text):
        try:
            response = ollama.embeddings(model=self.embedding_model, prompt=text)
            embedding = response["embedding"]
            embedding = np.array(embedding).tolist()  # Convert to list if needed
            logger.info(f"Embedding generated for text: {text[:50]}...")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding for text: {text[:50]}... Error: {e}")
            return np.random.rand(self.dimension).astype('float32').tolist()  # Placeholder

    def search(self, query, top_k=5):
        embedding = self.embed_text(query)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k
        )
        return [doc for doc in results['documents'][0]]

def create_vector_store(chunks):
    vector_store = VectorStore()
    vector_store.add_documents(chunks)
    return vector_store
