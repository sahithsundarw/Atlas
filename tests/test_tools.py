"""Smoke tests for individual tool functions. Requires valid API keys in .env."""
import pytest
from dotenv import load_dotenv

load_dotenv(override=True)

from agent.tools.weather import get_weather_forecast
from agent.tools.images import get_city_images
from agent.tools.search import web_search_city


def test_weather_forecast_structure():
    result = get_weather_forecast("Paris")
    assert "forecast" in result
    assert len(result["forecast"]) > 0
    day = result["forecast"][0]
    assert "date" in day
    assert "temp_min_c" in day
    assert "temp_max_c" in day
    assert "condition" in day
    assert "precipitation_mm" in day


def test_weather_forecast_invalid_city():
    with pytest.raises(ValueError):
        get_weather_forecast("ZZZZNOTACITY99999")


def test_city_images_structure():
    result = get_city_images("Paris")
    assert "urls" in result
    assert "credits" in result
    assert len(result["urls"]) >= 1


def test_web_search_city_structure():
    result = web_search_city("Paris")
    assert "content" in result
    assert len(result["content"]) > 100
