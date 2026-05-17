# run this once before starting the app: python data/seed_vectorstore.py
import os
import logging
from pathlib import Path

import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent / "seed_cities"
COLLECTION_NAME = "city_knowledge"
EMBED_MODEL = "text-embedding-3-small"
CITY_FILES = {
    "Paris": "paris.md",
    "Tokyo": "tokyo.md",
    "New York": "new_york.md",
    "London": "london.md",
    "Barcelona": "barcelona.md",
    "Dubai": "dubai.md",
    "Bali": "bali.md",
    "Sydney": "sydney.md",
    "Rome": "rome.md",
}


def embed_texts(texts: list[str], client: OpenAI) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def main() -> None:
    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
    chroma = chromadb.PersistentClient(path=persist_dir)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() > 0:
        logger.info("Collection already seeded (%d docs). Skipping.", collection.count())
        return

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    for city, filename in CITY_FILES.items():
        text = (SEED_DIR / filename).read_text(encoding="utf-8")
        chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
        embeddings = embed_texts(chunks, openai_client)

        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=[f"{city}_{i}" for i in range(len(chunks))],
            metadatas=[{"city": city, "chunk_index": i} for i in range(len(chunks))],
        )
        print(f"seeded {len(chunks)} chunks for {city}")

    print(f"done. total docs in collection: {collection.count()}")


if __name__ == "__main__":
    main()
