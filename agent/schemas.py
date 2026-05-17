from pydantic import BaseModel
from typing import Literal


class WeatherDay(BaseModel):
    date: str
    temp_min_c: float
    temp_max_c: float
    condition: str
    precipitation_mm: float


class FinalResponse(BaseModel):
    city: str
    city_summary: str
    weather_forecast: list[WeatherDay]
    image_urls: list[str]
    source: Literal["vector", "web", "seasonal"]
    similarity_score: float = 0.0
    fetched_at: str
