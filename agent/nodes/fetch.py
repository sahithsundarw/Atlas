import logging

from dotenv import load_dotenv

from ..state import AgentState
from ..tools.images import get_city_images
from ..tools.weather import get_weather_forecast

load_dotenv()
logger = logging.getLogger(__name__)


def weather_node(state: AgentState) -> dict:
    if state.get("intent") == "images_only":
        return {}
    # TODO: maybe add retry logic for flaky OWM responses

    city = state["city"]

    last_message = ""
    for m in reversed(state.get("messages", [])):
        if hasattr(m, "type") and m.type == "human":
            last_message = str(m.content)
            break

    try:
        raw = get_weather_forecast(
            city=city,
            intent=state.get("intent", ""),
            messages=list(state.get("messages", [])),
            user_question=last_message,
        )

        if raw.get("is_forecast_unavailable"):
            logger.info("weather_node: non-current period (%s) — no live forecast for %s", raw.get("month"), city)
            return {"weather": {}, "weather_raw": raw}

        logger.info("weather_node: got %d days for %s", len(raw.get("forecast", [])), city)
        return {"weather": raw, "weather_raw": raw}

    except Exception as exc:
        logger.error("weather_node failed: %s", exc)
        return {"errors": [f"Weather unavailable: {exc}"]}


def images_node(state: AgentState) -> dict:
    if state.get("intent") == "weather_only":
        return {}

    city = state["city"]
    search_query = state.get("image_search_query") or city
    try:
        result = get_city_images(city, search_query=search_query)
        urls    = result.get("urls", [])
        credits = result.get("credits", [])
        logger.info("images_node: got %d images for %s", len(urls), city)
        return {"images": urls, "image_credits": credits}
    except Exception as exc:
        logger.error("images_node failed: %s", exc)
        return {"errors": [f"Images unavailable: {exc}"]}
