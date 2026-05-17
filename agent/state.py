from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage
from operator import add


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]
    city: Optional[str]
    intent: Optional[str]
    image_search_query: Optional[str]
    source: Optional[str]
    retrieved_context: Optional[str]
    weather: Optional[dict]
    weather_raw: Optional[dict]   # raw return from weather tool before parsing
    images: Optional[list[str]]
    image_credits: Optional[list[dict]]
    final_response: Optional[dict]
    errors: Annotated[list[str], add]
