import os
import logging

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 2000


def web_search_city(city: str) -> dict:
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    results = client.search(
        query=f"travel guide {city}",
        search_depth="advanced",
        max_results=5,
    )
    parts = [r.get("content", "") for r in results.get("results", [])]
    combined = " ".join(parts)[:_MAX_CONTEXT_CHARS]  # cap it or compose blows up
    logger.info("Web search for %s returned %d chars", city, len(combined))
    return {"content": combined}


def extract_query_params(city: str, intent: str, image_search_query: str = "") -> dict:
    return {"city": city, "intent": intent, "image_search_query": image_search_query}
