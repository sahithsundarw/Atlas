import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from ..state import AgentState

load_dotenv()
logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a classifier. Respond with only 'yes' or 'no'.\n"
    "Is the following message a travel-related question? "
    "(asking about cities, destinations, weather, food, culture, transport, hotels, things to do, etc.)\n"
    "Say 'yes' if travel-related. Say 'no' if it is completely unrelated to travel."
)


def guard(state: AgentState) -> dict:
    last = ""
    for m in reversed(state.get("messages", [])):
        if hasattr(m, "type") and m.type == "human":
            last = str(m.content)
            break

    if not last:
        return {}

    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": last},
            ],
            max_tokens=3,
            temperature=0,
        )
        answer = resp.choices[0].message.content.strip().lower()
        if answer.startswith("no"):
            logger.info("guard: rejected non-travel query: %r", last[:80])
            return {"errors": ["I can only help with travel questions. Try asking about a city, destination, or travel tips!"]}
    except Exception as e:
        logger.warning("guard: classification failed (%s), allowing through", e)

    return {}
