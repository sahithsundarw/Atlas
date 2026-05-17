# Multi-Modal Travel Assistant — Atlas

A LangGraph-powered travel assistant that combines vector retrieval, live weather forecasts, city photography, and web search into a single conversational interface.

---

## Architecture

```
User Message
     │
     ▼
┌─────────────┐
│    guard    │  gpt-4o-mini classifies query — blocks non-travel questions
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  extract    │  OpenAI tool-call loop → city + intent
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   router    │  ChromaDB cosine similarity → "vector" or "web"
└──────┬──────┘
       │
   ┌───┴───────────┐
   ▼               ▼
┌────────┐    ┌─────────┐
│vector  │    │web      │   one branch runs, then both join fan_out
│fetch   │    │search   │
└────┬───┘    └────┬────┘
     └──────┬──────┘
            ▼ fan_out (parallel)
     ┌──────┴──────┐
     ▼             ▼
┌─────────┐  ┌─────────┐
│ weather │  │ images  │
└────┬────┘  └────┬────┘
     └──────┬──────┘
            ▼ join
     ┌─────────────┐
     │   compose   │  gpt-4o generates city_summary
     └──────┬──────┘
            ▼
       Final Response
```

The graph topology is visualised in `graph.png`.

---

## Key Features

- **Guardrails** — `guard` node rejects non-travel queries before they reach the LLM chain
- **Hybrid routing** — ChromaDB cosine similarity auto-selects knowledge base vs live web search
- **9 seed cities** — Paris, Tokyo, New York, London, Barcelona, Dubai, Bali, Sydney, Rome
- **Seasonal intelligence** — detects future/historical periods and responds with climate context instead of a missing forecast
- **Parallel fan-out** — weather + images fetched concurrently via LangGraph `Send`
- **Multi-turn memory** — `MemorySaver` checkpointer enables follow-up questions per `thread_id`
- **SSE streaming** — `/stream` endpoint pushes node-progress events to the browser in real time
- **Confidence badge** — similarity score shown in UI when routing via knowledge base
- **LangSmith tracing** — optional, enabled via `LANGCHAIN_TRACING_V2=true`
- **Docker** — `docker-compose up` starts both API and Streamlit services

---

## Distinction Challenges

### 1 — Manual OpenAI Tool-Call Loop (`agent/tools/registry.py`)

`run_with_tools()` implements the full loop without LangChain's built-in executor:

1. Filter `TOOL_SCHEMAS` to the allowed subset
2. Call `openai.chat.completions.create(... tools=schemas, tool_choice="auto")`
3. If the response has `tool_calls`, dispatch each to the matching Python function, wrap result as a `tool` message, and loop
4. Return when the model produces a message with no `tool_calls`

### 2 — Parallel Fan-Out with LangGraph `Send` (`agent/graph.py`)

Weather and images are fetched as **concurrent LangGraph tasks**. Total latency = slowest single call, not sum of all calls.

### 3 — MemorySaver Multi-Turn Memory

Compiled with `checkpointer=MemorySaver()`. Follow-ups ("What's the nightlife like?") work without re-sending history — the graph resumes from its last checkpoint for the `thread_id`.

---

## Project Structure

```
travel-assistant/
├── Atlas.html                  # Main UI — React 18 via CDN, no build step
├── app.jsx                     # React components
├── atlas.css                   # Theme tokens (light/dark)
├── api.py                      # FastAPI — POST /query, POST /stream
├── app.py                      # Streamlit UI (alternative)
├── tweaks-panel.jsx            # Live UI customisation panel
├── graph.png                   # LangGraph topology
├── Dockerfile
├── docker-compose.yml
├── agent/
│   ├── graph.py                # StateGraph, MemorySaver, stream_agent
│   ├── state.py                # AgentState TypedDict
│   ├── schemas.py              # Pydantic models
│   └── nodes/
│       ├── guard.py            # Travel-query guardrails
│       ├── extract.py          # Tool-call loop → city + intent
│       ├── router.py           # ChromaDB similarity routing
│       ├── retrieve.py         # Vector fetch for seed cities
│       ├── fetch.py            # Weather + images + web search
│       └── compose.py          # GPT-4o city_summary generation
│   └── tools/
│       ├── registry.py         # run_with_tools(), TOOLS, TOOL_SCHEMAS
│       ├── weather.py          # OpenWeatherMap forecast
│       ├── images.py           # Unsplash photo search
│       └── search.py           # Tavily web search
├── data/
│   ├── seed_cities/            # 9 city markdown files (~400 words each)
│   └── seed_vectorstore.py     # One-time ChromaDB ingestion (idempotent)
├── tests/
│   ├── test_tools.py           # API smoke tests
│   ├── test_tool_loop.py       # Tool-loop isolation test
│   └── eval.py                 # 25-case eval harness
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

| Variable | Where to get it |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com |
| `TAVILY_API_KEY` | app.tavily.com |
| `OPENWEATHERMAP_API_KEY` | openweathermap.org/api |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/developers |

LangSmith tracing is optional — set `LANGCHAIN_TRACING_V2=true` and add `LANGCHAIN_API_KEY`.

### 3. Seed the vector store

```bash
python data/seed_vectorstore.py
```

Embeds all 9 seed city documents into ChromaDB. Idempotent — safe to re-run (clears and re-seeds if collection exists).

### 4. Run

**Start the API:**
```bash
uvicorn api:app --reload
```

**Open the UI:** double-click `Atlas.html` or open it in any browser. Requires the API running on port 8000.

That's it — no build step, no npm, no bundler. The frontend is a single HTML file using React via CDN.

**Alternative — Streamlit:**
```bash
streamlit run app.py
```

**Alternative — Docker (both services):**
```bash
docker-compose up --build
```

---

## Routing Logic

| Condition | Branch | Source label |
|---|---|---|
| ChromaDB similarity ≥ 0.40 | `vector_fetch` | `"vector"` |
| Similarity < 0.40 | `web_search` | `"web"` |
| Future/historical period detected | either branch | `"seasonal"` |

---

## Running Tests

```bash
# unit + integration
python -m pytest tests/ -v

# eval harness (requires .env keys)
python -m pytest tests/eval.py -v -m eval
```

---

## Structured Output

```python
class FinalResponse(BaseModel):
    city: str
    city_summary: str
    weather_forecast: list[WeatherDay]
    image_urls: list[str]
    source: Literal["vector", "web", "seasonal"]
    similarity_score: float
    fetched_at: str
```
