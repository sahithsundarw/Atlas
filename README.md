# Atlas — Multi-Modal Travel Assistant

A LangGraph-powered travel assistant combining vector retrieval, live weather forecasts, city photography, and web search into a single conversational interface. Built with FastAPI + React (no bundler).

---

## Architecture

```
User Message
     │
     ▼
┌─────────────┐
│    guard    │  gpt-4o-mini — rejects non-travel queries
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
│vector  │    │web      │
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

Graph topology: `graph.png`

---

## Key Features

- **Guardrails** — `guard` node rejects non-travel queries via gpt-4o-mini before any LLM chain runs
- **Hybrid routing** — ChromaDB cosine similarity auto-selects knowledge base vs live web search (threshold 0.40)
- **9 seed cities** — Paris, Tokyo, New York, London, Barcelona, Dubai, Bali, Sydney, Rome
- **Seasonal intelligence** — detects future/historical periods, returns climate context instead of a missing forecast
- **Parallel fan-out** — weather + images fetched concurrently via LangGraph `Send`
- **Multi-turn memory** — `MemorySaver` checkpointer enables follow-up questions per `thread_id`
- **SSE streaming** — `/stream` endpoint pushes node-progress events to the browser
- **Confidence badge** — similarity score shown in UI for knowledge-base responses
- **LangSmith tracing** — optional, `LANGCHAIN_TRACING_V2=true`
- **Docker** — single `docker-compose up` starts the API

---

## Distinction Challenges

### 1 — Manual OpenAI Tool-Call Loop (`agent/tools/registry.py`)

`run_with_tools()` implements the full loop without LangChain's built-in executor:

1. Filter `TOOL_SCHEMAS` to the allowed subset
2. `openai.chat.completions.create(tools=schemas, tool_choice="auto")`
3. For each `tool_call` in the response: dispatch to the matching Python function, wrap result as a `tool` message, loop
4. Return when the model replies with no `tool_calls`

### 2 — Parallel Fan-Out (`agent/graph.py`)

Weather and images are fetched as concurrent LangGraph tasks via `Send`. Total latency = slowest single call, not the sum.

### 3 — MemorySaver Multi-Turn Memory

Compiled with `checkpointer=MemorySaver()`. Follow-ups like "What's the nightlife like?" resolve the city from the prior checkpoint — client sends no history.

---

## Project Structure

```
travel-assistant/
├── Atlas.html               # UI — React 18 via CDN, no build step
├── app.jsx                  # React components
├── atlas.css                # Theme tokens (light + dark)
├── tweaks-panel.jsx         # Live theme/accent customisation
├── api.py                   # FastAPI — POST /query, POST /stream
├── graph.png                # LangGraph topology diagram
├── run.ps1                  # Windows: start API + serve UI + open browser
├── run.sh                   # macOS/Linux equivalent
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── agent/
│   ├── graph.py             # StateGraph, MemorySaver, stream_agent
│   ├── state.py             # AgentState TypedDict
│   ├── schemas.py           # Pydantic models (WeatherDay, FinalResponse)
│   └── nodes/
│       ├── guard.py         # Non-travel query rejection
│       ├── extract.py       # city + intent extraction
│       ├── router.py        # ChromaDB similarity routing
│       ├── retrieve.py      # Vector fetch
│       ├── fetch.py         # Weather + images (parallel)
│       └── compose.py       # GPT-4o summary generation
│   └── tools/
│       ├── registry.py      # run_with_tools(), TOOLS, TOOL_SCHEMAS
│       ├── weather.py       # OpenWeatherMap forecast + seasonal detection
│       ├── images.py        # Unsplash photo search
│       └── search.py        # Tavily web search
├── data/
│   ├── seed_cities/         # 9 markdown files (~400 words each)
│   └── seed_vectorstore.py  # One-time ChromaDB ingestion (idempotent)
└── tests/
    ├── test_tools.py        # Tool-level smoke tests
    ├── test_tool_loop.py    # Tool-call loop isolation
    ├── smoke.py             # End-to-end API smoke tests
    └── eval.py              # 25-case eval harness
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
# fill in all four keys
```

| Variable | Source |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com |
| `TAVILY_API_KEY` | app.tavily.com |
| `OPENWEATHERMAP_API_KEY` | openweathermap.org/api |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/developers |

LangSmith (optional): set `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY`.

### 3. Seed the vector store

```bash
python data/seed_vectorstore.py
```

Embeds all 9 city documents into ChromaDB. Idempotent.

### 4. Run

**Windows:**
```powershell
.\run.ps1
```

**macOS / Linux:**
```bash
bash run.sh
```

Both scripts start the API on port 8000, serve the frontend on port 3000, and open `Atlas.html` in the browser automatically.

**Manual:**
```bash
uvicorn api:app --reload        # terminal 1
python -m http.server 3000      # terminal 2
# open http://localhost:3000/Atlas.html
```

**Docker:**
```bash
docker-compose up --build
# then open Atlas.html manually
```

---

## Routing Logic

| Condition | Branch | `source` field |
|---|---|---|
| ChromaDB similarity ≥ 0.40 | `vector_fetch` | `"vector"` |
| Similarity < 0.40 | `web_search` | `"web"` |
| Future / historical period | either branch | `"seasonal"` |

---

## Tests

```bash
# tool + loop tests
python -m pytest tests/test_tools.py tests/test_tool_loop.py -v

# end-to-end smoke (requires API running)
python tests/smoke.py

# eval harness
python -m pytest tests/eval.py -v -m eval
```

---

## API

**POST /query**
```json
{ "message": "Tell me about Tokyo", "thread_id": "abc123" }
```

**POST /stream** — SSE, same body. Emits `progress` events per node then a final `done` event.

**Response schema:**
```python
class FinalResponse(BaseModel):
    city: str
    city_summary: str
    weather_forecast: list[WeatherDay]
    image_urls: list[str]
    image_credits: list[dict]
    source: Literal["vector", "web", "seasonal"]
    similarity_score: float
    flag: str
    fetched_at: str
```
