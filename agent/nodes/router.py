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
    """ChromaDB distance <= 0.25 (similarity >= 0.75) routes to vector, else web."""
    city = state["city"]
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    resp = openai_client.embeddings.create(model=EMBED_MODEL, input=city)
    city_embedding = resp.data[0].embedding

    collection = _get_collection()

    if collection.count() == 0:
        logger.info("ChromaDB empty — routing to web_search for %s", city)
        return "web_search"

    results = collection.query(
        query_embeddings=[city_embedding],
        n_results=1,
        include=["distances"],
    )
    distance = results["distances"][0][0]
    similarity = 1 - distance

    logger.info("Router: city=%s similarity=%.3f threshold=%.2f", city, similarity, _SIMILARITY_THRESHOLD)

    if similarity >= _SIMILARITY_THRESHOLD:
        return "vector_fetch"
    return "web_search"


def router_node(state: AgentState) -> dict:
    return {}
