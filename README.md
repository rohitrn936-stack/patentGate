# PatentGate

AI-assisted **patent-risk research**. A user describes a product (with an
optional image); a multi-agent pipeline extracts its technical features,
searches prior art, argues where patent claim elements could overlap, argues the
distinctions back, proposes design-around alternatives, renders before/after
concept images, scores the exposure in a risk matrix, and writes a consolidated
report - all **streamed to the UI stage-by-stage** over Server-Sent Events.

> PatentGate is a research aid, **not legal advice**. The patent search is
> best-effort and not exhaustive. Every agent is prompted to avoid legal
> conclusions, and the disclaimers it returns are shown verbatim in the UI.

---

## What's in the repo

```
patentGate/
├── llm/                  Provider-agnostic LLM layer (OpenAI/Anthropic/Gemini/OpenRouter/local)
├── agent1/               Feature extraction + knowledge analysis (text + vision)
├── patent_search/        Prior-art retrieval: PatentsView → Google Patents → Tavily → stubs
├── agent2/               Prosecutor  (claim-element mappings that could read on the product)
├── agent3/               Defender    (distinctions / gaps / weak elements)
├── agent4/               Design-Around Engineer (exactly 3 alternative designs)
├── image_genration/      Before/After DALL-E concept images (best-effort, non-blocking)
├── risk_matrix/          Deterministic risk scoring (no LLM)
├── report_agent/         Final consolidated report + "questions for your attorney"
├── backend/              FastAPI + async SQLAlchemy: auth, products, analyses, SSE orchestration
├── frontend/             Next.js (App Router) + Tailwind + shadcn/ui + streaming analysis view
├── pyproject.toml        Installs `llm` + every agent package (editable)
└── docs/                 ARCHITECTURE.md · PROVIDERS.md · AUTH.md
```

### Request flow

```
Browser (Next.js)
  → POST /api/auth/login                       → JWT access + refresh token
  → POST /api/products                         → product (+ optional image) owned by the user
  → POST /api/analyses                         → analysis row (status: pending)
  → GET  /api/analyses/{id}/stream?token=…     → Server-Sent Events, one per stage:
        backend/app/services/pipeline.py  ::  stream_analysis_pipeline()
          FEATURE_EXTRACTION → PATENT_SEARCH (PATENT_FOUND ×5)
            → PROSECUTOR → DEFENDER → DESIGN_ENGINEER
            → RISK_MATRIX_READY → FINAL_REPORT_READY
            → REDESIGN_IMAGE_READY ×N → PIPELINE_COMPLETED
          every stage via llm.get_llm(agent=…); persisted to agent_runs (owner-scoped)
  → GET  /api/analyses/{id}                    → the full assembled result (rehydrates a reload)
```

`POST /api/analyses/{id}/run` still exists (fire-and-forget background task) for
non-streaming clients; it drains the same generator.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture.

---

## Quick start (local)

Requirements: Python 3.11+, Node 20+, and an API key for one LLM provider.

```bash
# 1. Python: one virtualenv for the whole repo
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # installs llm/ + agents + backend test deps
pip install -r backend/requirements.txt

# 2. Configure the LLM provider + the backend
cp .env.example .env             # set LLM_PROVIDER / LLM_MODEL / LLM_API_KEY
cp backend/.env.example backend/.env
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))" >> backend/.env

# 3. Run the backend (SQLite by default - no DB to install)
cd backend && uvicorn app.main:app --reload --port 8080

# 4. Run the frontend
cd frontend && npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_BACKEND_URL=http://localhost:8080
npm run dev                        # http://localhost:3000
```

Register a user in the UI, describe a product (optionally attach an image), and
the analysis view streams each stage in as it completes.

### Postgres instead of SQLite

Set `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/patentgate` in
`backend/.env` and run migrations:

```bash
cd backend && alembic upgrade head
```

---

## Choosing / switching the LLM provider

The agents never import a vendor SDK directly. Configuration is entirely
environment-driven (`.env`):

```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6          # the spec's model for agents 1-4 + the report
LLM_API_KEY=sk-ant-...

IMAGE_LLM_PROVIDER=openai            # image generation is a separate modality
IMAGE_LLM_MODEL=dall-e-3
IMAGE_LLM_API_KEY=sk-...             # falls back to OPENAI_API_KEY

PATENTSVIEW_API_KEY=                 # optional; free key at patentsview.org
TAVILY_API_KEY=                      # optional; enables web-search prior art
```

Supported out of the box: `openai`, `anthropic`, `gemini`, `openrouter`,
`local` (Ollama / vLLM / LM Studio). Any `LLM_*` variable can be prefixed with
an agent name for a per-agent override, e.g. `AGENT2_LLM_MODEL=gpt-4o` or
`REPORT_LLM_MODEL=…`. Adding a new provider is one file — see
[`docs/PROVIDERS.md`](docs/PROVIDERS.md).

The patent search layer degrades gracefully: with no `PATENTSVIEW_API_KEY` it
uses the credential-free Google Patents endpoint, then Tavily (if keyed), then
falls back to concept-derived stubs so the pipeline always has 5 results.
Set `PATENT_SEARCH_ENABLED=false` to skip the network entirely.

---

## Tests

```bash
source .venv/bin/activate
python -m pytest -q            # llm + all four agents + backend  (SQLite, no network)

cd frontend
npm run lint && npm run typecheck && npm run build
```

Backend tests use SQLite and the in-memory `FakeProvider` (`llm/testing.py`),
so they never touch a database server or a real model.

---

## Standalone agent servers (optional)

The backend runs the agents in-process (`IN_PROCESS_AGENTS=true`). Each agent
also ships a thin FastAPI server for LAN / debugging use:

```bash
uvicorn agent1.server:app --port 8001
uvicorn agent2.server:app --port 8002
uvicorn agent3.server:app --port 8003
uvicorn agent4.server:app --port 8004
```

---

## Security notes

- No secrets are committed; everything is `.env`-based and `.env` is git-ignored.
- In `APP_ENV=production` the backend refuses to start with a weak `JWT_SECRET`.
- All product/analysis data is scoped to the authenticated owner and enforced in
  the query layer (cross-user access returns `404`).
- See [`docs/AUTH.md`](docs/AUTH.md) for the token model and known trade-offs
  (e.g. the frontend stores tokens in `localStorage`).
