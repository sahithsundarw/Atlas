import datetime
import logging
import os
from collections import Counter

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_OWM_BASE = "https://api.openweathermap.org"
# TODO: cache geocoding results so we don't hit the API twice for the same city

_SEASON_MONTHS = {
    "winter": [12, 1, 2],
    "summer": [6, 7, 8],
    "spring": [3, 4, 5],
    "autumn": [9, 10, 11],
    "fall":   [9, 10, 11],
}

_SEASON_LABELS = {
    "winter":       "winter (December–February)",
    "summer":       "summer (June–August)",
    "spring":       "spring (March–May)",
    "autumn":       "autumn (September–November)",
    "fall":         "autumn (September–November)",
    "monsoon":      "monsoon season",
    "rainy season": "rainy season",
}

_MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

_YEAR_ROUND_PHRASES = [
    "year round", "year-round", "all year", "annually", "any time of year",
]


def is_non_current_period_query(messages: list = None, intent: str = "") -> tuple[bool, str]:
    full_text = (intent or "").lower()
    if messages:
        for m in messages[-4:]:
            full_text += " " + str(getattr(m, "content", "")).lower()

    current_month = datetime.datetime.now().month

    # Seasons
    for keyword, label in _SEASON_LABELS.items():
        if keyword in full_text:
            months = _SEASON_MONTHS.get(keyword)
            if months is None:
                return True, label  # monsoon / rainy season — always flag
            if current_month not in months:
                return True, label

    # Specific months
    for idx, month_key in enumerate(_MONTH_NAMES):
        if month_key in full_text:
            month_num = idx + 1
            if month_num != current_month:
                return True, month_key.capitalize()

    # Year-round / vague multi-period phrases
    for phrase in _YEAR_ROUND_PHRASES:
        if phrase in full_text:
            return True, "the full year"

    return False, None


def get_climate_context(city: str, period: str, user_question: str = "") -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""The user asked: "{user_question}"

Provide accurate climate information for {city} during {period}.

Include:
1. Average temperature range (°C)
2. Typical precipitation / conditions
3. Direct answer to whether their specific activity or concern is suitable
4. What to pack / practical advice

Be specific, factual, and directly answer their question. 3-5 sentences."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )
    return response.choices[0].message.content


def get_weather_forecast(
    city: str,
    intent: str = "",
    messages: list = None,
    user_question: str = "",
    state: dict = None,
) -> dict:
    # allow callers to pass state dict as fallback
    if state:
        intent        = intent or state.get("intent", "")
        messages      = messages or state.get("messages", [])
        user_question = user_question or ""

    is_future, period_label = is_non_current_period_query(messages=messages, intent=intent)
    if is_future and period_label:
        logger.info("weather: non-current period detected (%s) — skipping live forecast", period_label)
        climate = get_climate_context(city, period_label, user_question=user_question)
        return {
            "is_forecast_unavailable": True,
            "reason": (
                f"Live forecast for {period_label} is not available — "
                "weather APIs only cover the next 5 days."
            ),
            "climate_context": climate,
            "month": period_label,
            "city": city,
        }

    api_key = os.environ["OPENWEATHERMAP_API_KEY"]

    geo_resp = requests.get(
        f"{_OWM_BASE}/geo/1.0/direct",
        params={"q": city, "limit": 1, "appid": api_key},
        timeout=10,
    )
    geo_resp.raise_for_status()
    geo_data = geo_resp.json()
    if not geo_data:
        raise ValueError(f"City not found: {city}")

    lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
    logger.info("Geocoded %s → lat=%s lon=%s", city, lat, lon)

    forecast_resp = requests.get(
        f"{_OWM_BASE}/data/2.5/forecast",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
        timeout=10,
    )
    forecast_resp.raise_for_status()
    raw = forecast_resp.json()

    daily: dict[str, dict] = {}
    for item in raw["list"]:
        date = item["dt_txt"][:10]
        if date not in daily:
            daily[date] = {"temp_mins": [], "temp_maxs": [], "conditions": [], "precip": 0.0}
        daily[date]["temp_mins"].append(item["main"]["temp_min"])
        daily[date]["temp_maxs"].append(item["main"]["temp_max"])
        daily[date]["conditions"].append(item["weather"][0]["description"])
        daily[date]["precip"] += item.get("rain", {}).get("3h", 0.0)

    forecast = []
    for date, agg in sorted(daily.items()):
        forecast.append({
            "date": date,
            "temp_min_c": round(min(agg["temp_mins"]), 1),
            "temp_max_c": round(max(agg["temp_maxs"]), 1),
            "condition": Counter(agg["conditions"]).most_common(1)[0][0].capitalize(),
            "precipitation_mm": round(agg["precip"], 1),
        })

    return {"forecast": forecast}
