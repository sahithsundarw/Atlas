import logging
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes.compose import compose
from .nodes.extract import extract_intent
from .nodes.fetch import images_node, weather_node
from .nodes.guard import guard
from .nodes.retrieve import vector_fetch, web_search
from .nodes.router import route, router_node
from .state import AgentState

load_dotenv()
logger = logging.getLogger(__name__)

# LangSmith tracing — set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env to enable
if os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true":
    os.environ.setdefault("LANGCHAIN_PROJECT", "atlas-travel-assistant")
    logger.info("LangSmith tracing enabled")

_checkpointer = MemorySaver()
_graph = None  # lazy init so we don't build at import time


def _fan_out(state: AgentState) -> dict:
    return {}


def _join(state: AgentState) -> dict:
    return {}


def _route_by_source(state: AgentState) -> Literal["vector_fetch", "web_search"]:
    return route(state)


def _guard_edge(state: AgentState) -> Literal["extract_intent", "__end__"]:
    if state.get("errors"):
        return "__end__"
    return "extract_intent"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("guard", guard)
    workflow.add_node("extract_intent", extract_intent)
    workflow.add_node("router", router_node)
    workflow.add_node("vector_fetch", vector_fetch)
    workflow.add_node("web_search", web_search)
    workflow.add_node("fan_out", _fan_out)
    workflow.add_node("weather", weather_node)
    workflow.add_node("images", images_node)
    workflow.add_node("join", _join)
    workflow.add_node("compose", compose)

    workflow.set_entry_point("guard")
    workflow.add_conditional_edges(
        "guard",
        _guard_edge,
        {"extract_intent": "extract_intent", "__end__": END},
    )
    workflow.add_edge("extract_intent", "router")
    workflow.add_conditional_edges(
        "router",
        _route_by_source,
        {"vector_fetch": "vector_fetch", "web_search": "web_search"},
    )
    workflow.add_edge("vector_fetch", "fan_out")
    workflow.add_edge("web_search", "fan_out")
    workflow.add_edge("fan_out", "weather")
    workflow.add_edge("fan_out", "images")
    workflow.add_edge("weather", "join")
    workflow.add_edge("images", "join")
    workflow.add_edge("join", "compose")
    workflow.add_edge("compose", END)

    return workflow.compile(checkpointer=_checkpointer)


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_agent(user_input: str, thread_id: str) -> dict:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )

    if result.get("errors") and not result.get("final_response"):
        return {"errors": result["errors"]}

    if result.get("final_response"):
        response = result["final_response"]
        if result.get("image_credits"):
            response["image_credits"] = result["image_credits"]
        if result.get("errors"):
            response["errors"] = result["errors"]
        return response

    return {
        "errors": result.get("errors", ["Unknown error — no final_response generated"]),
    }


def stream_agent(user_input: str, thread_id: str):
    """Yield graph node-completion events as SSE-friendly dicts."""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    node_labels = {
        "guard":          "Checking query...",
        "extract_intent": "Extracting city and intent...",
        "router":         "Routing to knowledge source...",
        "vector_fetch":   "Loading from knowledge base...",
        "web_search":     "Searching the web...",
        "fan_out":        "Fetching weather and photos...",
        "weather":        "Getting forecast...",
        "images":         "Loading photos...",
        "join":           "Processing results...",
        "compose":        "Writing summary...",
    }

    final_state = {}
    for event in graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="updates",
    ):
        for node_name, node_output in event.items():
            label = node_labels.get(node_name, node_name)
            yield {"event": "progress", "node": node_name, "label": label}
            final_state.update(node_output or {})

    if final_state.get("errors") and not final_state.get("final_response"):
        yield {"event": "error", "errors": final_state["errors"]}
        return

    if final_state.get("final_response"):
        response = final_state["final_response"]
        if final_state.get("image_credits"):
            response["image_credits"] = final_state["image_credits"]
        yield {"event": "done", "data": response}
    else:
        yield {"event": "error", "errors": ["No response generated"]}
