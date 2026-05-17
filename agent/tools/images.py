import os
import logging

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_UNSPLASH_BASE = "https://api.unsplash.com"


def get_city_images(city: str, count: int = 6, search_query: str = "") -> dict:
    access_key = os.environ["UNSPLASH_ACCESS_KEY"]
    query = search_query if search_query else city

    resp = requests.get(
        f"{_UNSPLASH_BASE}/search/photos",
        params={"query": query, "per_page": count, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {access_key}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    urls = []
    credits = []
    for r in data.get("results", []):
        urls.append(r["urls"]["regular"])  # regular size is fine, full is too large
        credits.append({"name": r["user"]["name"], "link": r["user"]["links"]["html"]})

    logger.info("Fetched %d images for %s", len(urls), city)
    return {"urls": urls, "credits": credits}
