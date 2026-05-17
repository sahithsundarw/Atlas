import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from openai import OpenAI

from ..schemas import FinalResponse, WeatherDay
from ..state import AgentState

load_dotenv(override=True)
logger = logging.getLogger(__name__)


def _fix_mojibake(text: str) -> str:
    """Reverse UTF-8-decoded-as-Latin-1 mojibake (e.g. 'Â°' → '°').

    Whole-string encode('latin-1') fails on mixed content (smart quotes, em-dashes).
    Fall back to scanning adjacent char pairs that form valid 2-byte UTF-8 sequences.
    """
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    result = []
    chars = list(text)
    i = 0
    while i < len(chars):
        cp = ord(chars[i])
        if 0xC0 <= cp <= 0xDF and i + 1 < len(chars):
            nxt = ord(chars[i + 1])
            if 0x80 <= nxt <= 0xBF:
                try:
                    result.append(bytes([cp, nxt]).decode("utf-8"))
                    i += 2
                    continue
                except UnicodeDecodeError:
                    pass
        result.append(chars[i])
        i += 1
    return "".join(result)


_TOPIC_MISMATCHES = {
    "nightlife": ["outdoor activities", "hiking", "nature trail", "temple visit"],
    "restaurants": ["outdoor activities", "hiking", "nightlife", "clubs"],
    "outdoor": ["nightlife", "bars", "clubs", "restaurants"],
    "hotels": ["nightlife", "outdoor activities", "restaurants"],
}


def _build_messages(state: AgentState, last_user_message: str) -> list[dict]:
    city = state.get("city", "")
    intent = state.get("intent", "general")
    context = state.get("retrieved_context", "")
    weather = state.get("weather", {})

    weather_preview = json.dumps(
        (weather.get("forecast", []) if isinstance(weather, dict) else [])[:3]
    )
    clean_context = _fix_mojibake(context[:800] if context else "")

    system_prompt = f"""You are Atlas, a travel assistant. Answer ONLY the user's current question.

CURRENT QUESTION: "{last_user_message}"
CITY: {city}
TOPIC: {intent}

STRICT RULES:
1. Answer the CURRENT QUESTION only. Do not mention previous questions or answers.
2. If the topic is "trek" or "hiking" — describe treks, routes, difficulty, best season.
3. If the topic is "weather" — describe current/seasonal conditions specifically.
4. If the topic is "family activities" or "things to do" — describe family-friendly activities.
5. If the topic is "restaurants" or "food" — describe dining options.
6. NEVER start your answer with the same sentence as a previous answer.
7. city_summary must be 3-5 sentences directly answering the current question.
8. Do not mention "Markha Valley Trek" unless the user specifically asked about it.

Background context: {clean_context}
This week's weather: {weather_preview}
"""

    user_prompt = (
        f'Answer this specific question: "{last_user_message}"\n\n'
        f'Return ONLY valid JSON: {{"city_summary": "<3-5 sentences answering ONLY: {last_user_message}>"}}'
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _is_wrong_topic(summary: str, intent: str) -> bool:
    wrong_phrases = _TOPIC_MISMATCHES.get(intent.lower(), [])
    return any(phrase in summary.lower() for phrase in wrong_phrases)


def compose(state: AgentState) -> dict:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    city        = state["city"]
    weather     = state.get("weather", {})
    weather_raw = state.get("weather_raw", {})
    images      = state.get("images", [])
    source      = state.get("source", "web")
    intent      = state.get("intent", "general")

    last_user_message = ""
    for m in reversed(state.get("messages", [])):
        role = getattr(m, "type", None) or getattr(m, "role", None)
        if role in ("human", "user"):
            last_user_message = str(m.content)
            break

    logger.info("compose: last_user_message=%r intent=%s city=%s", last_user_message, intent, city)

    use_forecast = True
    if isinstance(weather_raw, dict) and weather_raw.get("is_forecast_unavailable"):
        period      = weather_raw.get("month", "that period")
        climate_ctx = weather_raw.get("climate_context", "")
        use_forecast = False
        source = "seasonal"
        logger.info("compose: non-current period (%s), building seasonal response", period)

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are Atlas, a travel assistant. The user asked about {city} during {period}.\n\n"
                    "A live forecast is not available for that period (our weather API only covers the next 5 days).\n\n"
                    f"Here is climate research for that period:\n{climate_ctx}\n\n"
                    "Write city_summary as a 4-6 sentence response that:\n"
                    "1. Directly answers their question using the climate data above\n"
                    "2. Gives practical advice (what to wear, what to expect, best/worst days)\n"
                    "3. Does NOT mention 'API' or 'forecast unavailable' — just answer naturally\n"
                    "4. Does NOT reference the current week's weather at all\n\n"
                    "Answer ONLY the current question. Do not reference previous answers."
                ),
            },
            {
                "role": "user",
                "content": (
                    f'Answer this specific question: "{last_user_message}"\n\n'
                    f'Return valid JSON only: {{"city_summary": "<4-6 sentences about {period} in {city}>"}}'
                ),
            },
        ]
    else:
        messages = _build_messages(state, last_user_message)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=400,
    )

    city_summary = f"{city} is a fascinating destination."
    try:
        parsed = json.loads(response.choices[0].message.content)
        city_summary = _fix_mojibake(parsed.get("city_summary", city_summary))
        # print(f"DEBUG city_summary: {city_summary[:80]}")
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("compose: failed to parse summary JSON (%s), using fallback", e)

    if _is_wrong_topic(city_summary, intent):
        logger.warning("compose: topic drift detected (intent=%s) — retrying", intent)
        retry_messages = messages + [
            {"role": "assistant", "content": json.dumps({"city_summary": city_summary})},
            {
                "role": "user",
                "content": (
                    f"IMPORTANT: Your previous response was about the wrong topic. "
                    f'The user asked: "{last_user_message}". '
                    f'Write ONLY about {intent} in {city}. '
                    f'Return JSON: {{"city_summary": "<answer about {intent} only>"}}'
                ),
            },
        ]
        retry_response = client.chat.completions.create(
            model="gpt-4o",
            messages=retry_messages,
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=400,
        )
        try:
            city_summary = _fix_mojibake(
                json.loads(retry_response.choices[0].message.content).get("city_summary", city_summary)
            )
        except (json.JSONDecodeError, KeyError):
            pass

    weather_forecast: list[WeatherDay] = []
    if use_forecast and weather and "forecast" in weather:
        for day in weather["forecast"]:
            try:
                weather_forecast.append(WeatherDay(**day))
            except Exception as exc:
                logger.warning("WeatherDay validation failed for %s: %s", day, exc)

    final = FinalResponse(
        city=city,
        city_summary=city_summary,
        weather_forecast=weather_forecast,
        image_urls=images or [],
        source=source,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        "compose: built FinalResponse for %s (intent=%s, source=%s, weather_days=%d, images=%d)",
        city, intent, source, len(weather_forecast), len(images or []),
    )

    return {
        "final_response": final.model_dump(),
        "messages": [AIMessage(content=f"Here is your travel information for {city}.")],
    }
