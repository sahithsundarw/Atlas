# Multi-Modal Travel Assistant — Atlas

A LangGraph-powered travel assistant that combines vector retrieval, live weather forecasts, city photography, and web search into a single conversational interface. Built for the AI Engineer Assignment.

---

## Architecture

```
User Message
     │
     ▼
┌─────────────┐
│  extract    │  OpenAI tool-call loop → city + intent (full / weather_only / images_only)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   router    │  ChromaDB similarity check → "vector" if seed city exists, else "web"
└──────┬──────┘
       │
   ┌───┴────────────────────┐
   ▼                        ▼
┌────────┐           ┌────────────┐
│retrieve│           │   fetch    │   (parallel fan-out via LangGraph Send)
│(vector)│           │(weather +  │
└────┬───┘           │ images +   │
     │               │ web search)│
     │               └─────┬──────┘
     └──────────┬───────────┘
                ▼
        ┌─────────────┐
        │   compose   │  OpenAI generates city_summary from retrieved context
        └──────┬──────┘
               │
               ▼
          Final Response
    {city, city_summary, weather_forecast,
     image_urls, image_credits, source, flag}
```

The graph topology is visualised in `graph.png`.

---

## Distinction Challenges

### 1 — Manual OpenAI Tool-Call Loop (`agent/tools/registry.py`)

The extract node does **not** use LangChain's built-in tool executor. Instead `run_with_tools()` implements the full loop manually:

1. Filter `TOOL_SCHEMAS` to the allowed subset
2. Call `openai.chat.completions.create(... tools=schemas, tool_choice="auto")`
3. If the response contains `tool_calls`, dispatch each to the matching Python function in `TOOLS`, wrap the result as a `tool` role message, and loop
4. Return when the model produces a message with no `tool_calls`

This gives full control over which tools are available per node, retry logic, and observability.

### 2 — Parallel Fan-Out with LangGraph `Send` (`agent/graph.py`)

The fetch node fans out weather, images, and (when needed) web search as **concurrent LangGraph tasks** using `Send`. All three API calls run in parallel before the compose node aggregates the results. This cuts total latency to the slowest single call rather than the sum of all three.

### 3 — MemorySaver Multi-Turn Memory (`agent/graph.py`)

The graph is compiled with `checkpointer=MemorySaver()`. Every request includes a `thread_id`; LangGraph replays the full state for that thread on each call. This enables true follow-up questions ("What's the nightlife like?", "Is it safe for solo travel?") without the client re-sending history — the graph resumes from its last checkpoint automatically.

---

## Project Structure

```
travel-assistant/
├── app.py                      # Streamlit UI (two-column layout, Plotly weather chart)
├── api.py                      # FastAPI server — POST /query
├── Atlas.html                  # Standalone browser UI (React 18 via CDN)
├── app.jsx                     # React frontend components
├── atlas.css                   # Theme tokens (light/dark)
├── tweaks-panel.jsx            # Live UI customisation panel
├── graph.png                   # LangGraph topology visualisation
├── agent/
│   ├── graph.py                # StateGraph definition, MemorySaver, Send fan-out
│   ├── state.py                # AgentState TypedDict
│   ├── schemas.py              # Pydantic models (WeatherDay, FinalResponse)
│   └── nodes/
│       ├── extract.py          # Tool-call loop → city + intent
│       ├── router.py           # ChromaDB similarity → vector / web branch
│       ├── retrieve.py         # ChromaDB query for seed cities
│       ├── fetch.py            # Parallel weather + images + web search
│       └── compose.py          # OpenAI city_summary generation
│   └── tools/
│       ├── registry.py         # run_with_tools(), TOOLS, TOOL_SCHEMAS
│       ├── weather.py          # OpenWeatherMap forecast
│       ├── images.py           # Unsplash photo search
│       └── search.py           # Tavily web search + extract_query_params
├── data/
│   ├── seed_cities/            # paris.md, tokyo.md, new_york.md (~400 words each)
│   └── seed_vectorstore.py     # One-time ChromaDB ingestion (idempotent)
├── tests/
│   ├── test_tools.py           # Smoke tests for each API tool
│   └── test_tool_loop.py       # Manual tool-loop isolation test
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in all four keys:

| Variable | Where to get it |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com |
| `TAVILY_API_KEY` | app.tavily.com |
| `OPENWEATHERMAP_API_KEY` | openweathermap.org/api |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/developers |

### 3. Seed the vector store

```bash
python data/seed_vectorstore.py
```

Embeds the three seed city documents into ChromaDB at `./chroma_db`. Idempotent — safe to re-run.

### 4. Run

**Streamlit (assignment submission):**
```bash
streamlit run app.py
```

**FastAPI backend (for browser UI):**
```bash
uvicorn api:app --reload
```

**Browser UI:** open `Atlas.html` directly (requires FastAPI running on port 8000).

---

## Routing Logic

| Condition | Branch | Data source |
|---|---|---|
| City matches a seed document (ChromaDB similarity > threshold) | `vector` | Local ChromaDB chunk |
| No seed match | `web` | Tavily web search |

Both branches then fetch live weather (OpenWeatherMap 5-day/3-hour forecast) and photos (Unsplash) in parallel.

---

## Structured Output

All responses conform to `agent/schemas.py`:

```python
class FinalResponse(BaseModel):
    city: str
    city_summary: str
    weather_forecast: list[WeatherDay]   # date, temp_min_c, temp_max_c, condition, precipitation_mm
    image_urls: list[str]
    source: Literal["vector", "web"]
    fetched_at: str
```

The compose node extracts `city_summary` from an OpenAI JSON-mode response. Weather and image data come directly from tool calls, never hallucinated.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

`test_tools.py` — live API smoke tests (requires `.env` keys)  
`test_tool_loop.py` — verifies the manual tool-call loop terminates correctly
