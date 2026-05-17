"""End-to-end evaluation tests for the Atlas Travel API.

Requires the FastAPI server running at http://localhost:8000.
Run with: pytest tests/eval.py -m eval -v
"""
import re
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_URL = "http://localhost:8000"
QUERY_URL = f"{BASE_URL}/query"
HEALTH_URL = f"{BASE_URL}/health"


def _server_up() -> bool:
    try:
        r = requests.get(HEALTH_URL, timeout=5)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


if not _server_up():
    pytest.skip("Atlas API server is not running at http://localhost:8000", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def query(message: str, thread_id: str | None = None) -> dict:
    if thread_id is None:
        thread_id = str(uuid.uuid4())
    resp = requests.post(QUERY_URL, json={"message": message, "thread_id": thread_id}, timeout=60)
    resp.raise_for_status()
    return resp.json()


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HTTPS_RE = re.compile(r"^https://")


# ---------------------------------------------------------------------------
# 1. Seed cities → source="vector"
# ---------------------------------------------------------------------------

@pytest.mark.eval
@pytest.mark.parametrize("city", [
    "Paris",
    "Tokyo",
    "New York",
    "London",
    "Barcelona",
    "Dubai",
    "Bali",
    "Sydney",
    "Rome",
])
def test_seed_city_routes_to_vector(city):
    data = query(f"Tell me about {city}")
    assert "error" not in data, f"API returned error: {data.get('error')}"
    assert data.get("source") == "vector", (
        f"{city}: expected source='vector', got source={data.get('source')!r}"
    )


# ---------------------------------------------------------------------------
# 2. Unknown cities → source="web"
# ---------------------------------------------------------------------------

@pytest.mark.eval
@pytest.mark.parametrize("city", ["Reykjavik", "Lima"])
def test_unknown_city_routes_to_web(city):
    data = query(f"Tell me about {city}")
    assert "error" not in data, f"API returned error: {data.get('error')}"
    assert data.get("source") == "web", (
        f"{city}: expected source='web', got source={data.get('source')!r}"
    )


# ---------------------------------------------------------------------------
# 3. Seasonal queries → source="seasonal", 0 forecast days
# ---------------------------------------------------------------------------

@pytest.mark.eval
@pytest.mark.parametrize("message", [
    "Tokyo in winter",
    "Paris in summer",
])
def test_seasonal_query(message):
    data = query(message)
    assert "error" not in data, f"API returned error: {data.get('error')}"
    assert data.get("source") == "seasonal", (
        f"'{message}': expected source='seasonal', got source={data.get('source')!r}"
    )
    assert data.get("weather_forecast") == [], (
        f"'{message}': expected empty weather_forecast, got {data.get('weather_forecast')}"
    )


# ---------------------------------------------------------------------------
# 4. city_summary is non-empty and > 50 chars
# ---------------------------------------------------------------------------

@pytest.mark.eval
@pytest.mark.parametrize("message", [
    "Tell me about Paris",
    "Tell me about Tokyo",
    "Tell me about New York",
    "Tell me about Reykjavik",
    "Tokyo in winter",
])
def test_city_summary_non_empty(message):
    data = query(message)
    assert "error" not in data, f"API returned error: {data.get('error')}"
    summary = data.get("city_summary", "")
    assert isinstance(summary, str) and len(summary) > 50, (
        f"'{message}': city_summary too short or missing — got {summary!r}"
    )


# ---------------------------------------------------------------------------
# 5. weather_forecast items have correct fields and types
# ---------------------------------------------------------------------------

@pytest.mark.eval
@pytest.mark.parametrize("city", ["Paris", "Tokyo", "London"])
def test_weather_forecast_structure(city):
    data = query(f"Tell me about {city}")
    assert "error" not in data, f"API returned error: {data.get('error')}"
    forecast = data.get("weather_forecast", [])
    assert len(forecast) > 0, f"{city}: weather_forecast is empty"

    for i, day in enumerate(forecast):
        assert DATE_RE.match(day.get("date", "")), (
            f"{city} day[{i}]: date {day.get('date')!r} is not YYYY-MM-DD"
        )
        assert isinstance(day.get("temp_min_c"), (int, float)), (
            f"{city} day[{i}]: temp_min_c missing or wrong type"
        )
        assert isinstance(day.get("temp_max_c"), (int, float)), (
            f"{city} day[{i}]: temp_max_c missing or wrong type"
        )
        assert isinstance(day.get("condition"), str) and day["condition"], (
            f"{city} day[{i}]: condition missing or empty"
        )
        assert isinstance(day.get("precipitation_mm"), (int, float)), (
            f"{city} day[{i}]: precipitation_mm missing or wrong type"
        )


# ---------------------------------------------------------------------------
# 6. image_urls are valid https:// URLs
# ---------------------------------------------------------------------------

@pytest.mark.eval
@pytest.mark.parametrize("city", ["Paris", "Tokyo", "Sydney"])
def test_image_urls_are_https(city):
    data = query(f"Tell me about {city}")
    assert "error" not in data, f"API returned error: {data.get('error')}"
    urls = data.get("image_urls", [])
    assert len(urls) > 0, f"{city}: image_urls is empty"
    for url in urls:
        assert HTTPS_RE.match(url), f"{city}: image URL is not https — got {url!r}"


# ---------------------------------------------------------------------------
# 7. Multi-turn: city context persists across turns on same thread_id
# ---------------------------------------------------------------------------

@pytest.mark.eval
def test_multiturn_city_context_persists():
    thread_id = str(uuid.uuid4())

    first = query("Tell me about Paris", thread_id=thread_id)
    assert "error" not in first, f"First turn error: {first.get('error')}"
    assert first.get("city", "").lower() == "paris", (
        f"First turn: expected city='Paris', got {first.get('city')!r}"
    )

    second = query("What about the food?", thread_id=thread_id)
    assert "error" not in second, f"Second turn error: {second.get('error')}"
    assert second.get("city", "").lower() == "paris", (
        f"Second turn: expected city still 'Paris' from context, got {second.get('city')!r}"
    )
