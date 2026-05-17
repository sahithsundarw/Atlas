import logging
import os

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from ..state import AgentState

load_dotenv(override=True)
logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.40  # tuned by trial and error against Paris/Tokyo/NYC
# TODO: could cache city embeddings to avoid re-embedding on every request
COLLECTION_NAME = "city_knowledge"
EMBED_MODEL = "text-embedding-3-small"


def _get_collection():
    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def route(state: AgentState) -> str:
    """ChromaDB cosine distance maps to similarity; threshold 0.40 separates seed cities from unknowns."""
    return "vector_fetch" if state.get("similarity_score", 0) >= _SIMILARITY_THRESHOLD else "web_search"


def router_node(state: AgentState) -> dict:
    city = state["city"]
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    resp = openai_client.embeddings.create(model=EMBED_MODEL, input=city)
    city_embedding = resp.data[0].embedding

    collection = _get_collection()

    if collection.count() == 0:
        logger.info("ChromaDB empty — routing to web_search for %s", city)
        return {"similarity_score": 0.0}

    results = collection.query(
        query_embeddings=[city_embedding],
        n_results=1,
        include=["distances"],
    )
    distance = results["distances"][0][0]
    similarity = round(1 - distance, 4)

    logger.info("Router: city=%s similarity=%.3f threshold=%.2f", city, similarity, _SIMILARITY_THRESHOLD)
    return {"similarity_score": similarity}
