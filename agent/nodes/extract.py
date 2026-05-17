import json
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from ..state import AgentState

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are extracting query parameters from a user message in a travel assistant conversation.

The conversation history is provided. The user may ask follow-up questions that reference previous context.

Rules:
- If the user references a city from earlier in the conversation (e.g. "what about the nightlife?" "tell me more" "what's the weather like there?"), use that city.
- ALWAYS extract the actual CURRENT topic from the latest message, not from previous messages.
- "what about X?" means the topic is X, not whatever was discussed before.
- "tell me more about Y" means the topic is Y.

Extract:
{
  "city": "<city name, inferred from context if not stated>",
  "intent": "<specific topic from the LATEST user message — e.g. 'nightlife', 'restaurants', 'outdoor activities', 'weather', 'hotels', 'general'>",
  "image_search_query": "<city> <topic> — e.g. 'Kyoto nightlife bars', 'Tokyo restaurants food'>",
  "is_followup": <true if this references a previous message, false if new query>
}

Return only valid JSON, nothing else."""


def extract_intent(state: AgentState) -> dict:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in state["messages"][-6:]:
        if hasattr(msg, "type"):
            role = "user" if msg.type == "human" else "assistant"
            messages_for_llm.append({"role": role, "content": str(msg.content)})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages_for_llm,
        response_format={"type": "json_object"},
    )

    city = state.get("city")
    intent = state.get("intent", "full")
    image_search_query = state.get("image_search_query", "")

    try:
        parsed = json.loads(response.choices[0].message.content)
        city = parsed.get("city") or city
        intent = parsed.get("intent") or intent
        image_search_query = parsed.get("image_search_query") or f"{city} {intent}"
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("extract_intent: failed to parse JSON response: %s", exc)

    if not image_search_query:
        image_search_query = f"{city} landmarks travel"

    logger.info(
        "extract_intent: city=%s intent=%s image_search_query=%s is_followup=%s",
        city, intent, image_search_query,
        parsed.get("is_followup", False) if "parsed" in locals() else "?",
    )
    return {"city": city, "intent": intent, "image_search_query": image_search_query}
