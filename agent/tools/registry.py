import json
import logging
from typing import Callable

from .weather import get_weather_forecast
from .images import get_city_images
from .search import web_search_city, extract_query_params

logger = logging.getLogger(__name__)

TOOLS: dict[str, Callable] = {
    "get_weather_forecast": get_weather_forecast,
    "get_city_images": get_city_images,
    "web_search_city": web_search_city,
    "extract_query_params": extract_query_params,
}

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "extract_query_params",
            "description": "Extract city name and intent from the user message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city name mentioned by the user."},
                    "intent": {
                        "type": "string",
                        "enum": ["full", "weather_only", "images_only"],
                        "description": "What the user wants: full info, weather only, or images only.",
                    },
                    "image_search_query": {
                        "type": "string",
                        "description": "3-5 word Unsplash-optimized image search query derived from the user's question. Examples: 'Tokyo restaurants food dining', 'Kyoto nature hiking outdoor', 'Paris family attractions landmarks'",
                    },
                },
                "required": ["city", "intent", "image_search_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Get a multi-day weather forecast for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name."},
                    "days": {"type": "integer", "description": "Number of days (max 5 on free tier).", "default": 7},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_city_images",
            "description": "Fetch landscape photos of a city from Unsplash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name."},
                    "count": {"type": "integer", "description": "Number of images to return.", "default": 6},
                    "search_query": {"type": "string", "description": "Specific search query for images. Defaults to city name if omitted."},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_city",
            "description": "Search for travel guide content about a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name."},
                },
                "required": ["city"],
            },
        },
    },
]


def run_with_tools(messages: list, allowed_tools: list[str], openai_client) -> object:
    # manual tool loop - not using prebuilt ToolNode
    schemas = [s for s in TOOL_SCHEMAS if s["function"]["name"] in allowed_tools]

    while True:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=schemas,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg

        for call in msg.tool_calls:
            fn = TOOLS[call.function.name]
            args = json.loads(call.function.arguments)
            logger.info("Tool call: %s(%s)", call.function.name, args)
            try:
                result = fn(**args)
            except Exception as exc:
                result = {"error": str(exc)}
                logger.warning("Tool %s failed: %s", call.function.name, exc)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })
