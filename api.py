"""Atlas FastAPI backend — wraps LangGraph agent as a REST API."""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(override=True)

# Validate required env vars at startup — fail loudly rather than at first request
_REQUIRED = ["OPENAI_API_KEY", "OPENWEATHERMAP_API_KEY", "UNSPLASH_ACCESS_KEY", "TAVILY_API_KEY"]
_missing = [k for k in _REQUIRED if not os.environ.get(k)]
if _missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(_missing)}")

from agent.graph import get_graph, run_agent  # noqa: E402


_FLAGS: dict[str, str] = {
    "tokyo": "🇯🇵", "kyoto": "🇯🇵", "osaka": "🇯🇵",
    "paris": "🇫🇷", "nice": "🇫🇷", "lyon": "🇫🇷",
    "new york": "🇺🇸", "nyc": "🇺🇸", "chicago": "🇺🇸", "los angeles": "🇺🇸",
    "london": "🇬🇧", "edinburgh": "🇬🇧",
    "rome": "🇮🇹", "milan": "🇮🇹", "florence": "🇮🇹",
    "barcelona": "🇪🇸", "madrid": "🇪🇸",
    "bangkok": "🇹🇭", "dubai": "🇦🇪", "singapore": "🇸🇬",
    "sydney": "🇦🇺", "melbourne": "🇦🇺",
    "amsterdam": "🇳🇱", "berlin": "🇩🇪", "munich": "🇩🇪",
    "toronto": "🇨🇦", "vancouver": "🇨🇦",
    "istanbul": "🇹🇷", "prague": "🇨🇿", "vienna": "🇦🇹",
}


def get_flag(city: str) -> str:
    return _FLAGS.get(city.lower().strip(), "🌐")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_graph()  # pre-warm graph + MemorySaver
    yield


app = FastAPI(title="Atlas Travel API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class QueryRequest(BaseModel):
    message: str
    thread_id: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/query")
async def query(body: QueryRequest) -> dict:
    try:
        result = run_agent(body.message, body.thread_id)
    except Exception as exc:
        return {"error": str(exc)}

    if not result.get("city"):
        errors = result.get("errors", ["Unknown error"])
        return {"error": " | ".join(errors)}

    return {
        "city": result.get("city", ""),
        "city_summary": result.get("city_summary", ""),
        "weather_forecast": result.get("weather_forecast", []),
        "image_urls": result.get("image_urls", []),
        "image_credits": result.get("image_credits", []),
        "source": result.get("source", "web"),
        "fetched_at": result.get("fetched_at", ""),
        "flag": get_flag(result.get("city", "")),
        "errors": result.get("errors", []),
    }
