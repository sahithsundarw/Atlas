import logging
import os

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

from ..state import AgentState
from ..tools.search import web_search_city

load_dotenv()
logger = logging.getLogger(__name__)

COLLECTION_NAME = "city_knowledge"
EMBED_MODEL = "text-embedding-3-small"


def vector_fetch(state: AgentState) -> dict:
    city = state["city"]
    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    resp = openai_client.embeddings.create(model=EMBED_MODEL, input=city)
    city_embedding = resp.data[0].embedding

    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
    chroma = chromadb.PersistentClient(path=persist_dir)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    results = collection.query(
        query_embeddings=[city_embedding],
        n_results=3,
        include=["documents"],
    )
    docs = results["documents"][0] if results["documents"] else []
    context = "\n\n".join(docs)
    # joining with double newline keeps paragraph structure intact
    logger.info("vector_fetch: retrieved %d chars for %s", len(context), city)

    return {"retrieved_context": context, "source": "vector"}


def web_search(state: AgentState) -> dict:
    city = state["city"]
    try:
        result = web_search_city(city)
        context = result.get("content", "")
    except Exception as exc:
        logger.warning("web_search: Tavily failed (%s), continuing with empty context", exc)
        context = ""

    logger.info("web_search: retrieved %d chars for %s", len(context), city)
    return {"retrieved_context": context, "source": "web"}
