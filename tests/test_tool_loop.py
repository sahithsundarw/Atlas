"""Isolation test for the manual tool-call execution loop."""
import os
import pytest
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

from agent.tools.registry import run_with_tools


def test_tool_loop_terminates():
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages = [{"role": "user", "content": "Get the weather forecast for Paris."}]
    result = run_with_tools(messages, ["get_weather_forecast"], client)
    assert result is not None
    assert not result.tool_calls


def test_tool_loop_extract_params():
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages = [{"role": "user", "content": "Tell me about Tokyo — I want weather and photos."}]
    result = run_with_tools(messages, ["extract_query_params"], client)
    assert result is not None
    assert not result.tool_calls
