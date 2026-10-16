# Architecture

## Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│ frontend/  Next.js App Router · Tailwind · shadcn/ui                 │
│   AuthProvider (localStorage tokens, auto-refresh) · typed API client│
└───────────────┬─────────────────────────────────────────────────────┘
                │  HTTPS + Bearer JWT
┌───────────────▼─────────────────────────────────────────────────────┐
│ backend/  FastAPI + async SQLAlchemy                                 │
│   routes/     auth · products · analyses · agent1                    │
│   dependencies/auth.get_current_user  (enforced on every data route) │
│   services/   auth · pipeline (in-process agent orchestration)       │
│   models/     users · products · analyses · agent_runs · patents …   │
│   middleware  request-id · security headers · body-size · CORS       │
│   errors      {error:{code,message,request_id}} envelope             │
└───────────────┬─────────────────────────────────────────────────────┘
                │  Python calls (asyncio.to_thread)
┌───────────────▼─────────────────────────────────────────────────────┐
│ agent1 · agent2 · agent3 · agent4 · risk_matrix · image_genration   │
│   each agent:  prompts + Pydantic contract + llm.get_llm(agent=...)  │
└───────────────┬─────────────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────────────┐
│ llm/   LLMProvider ABC · registry · env config · retry · errors     │
│   providers/  openai · anthropic · gemini · openrouter · local      │
└────────────────────────────────────────────────────────────────────┘
```

## The pipeline (`backend/app/services/pipeline.py`)

`stream_analysis_pipeline(analysis_id)` is an **async generator** that yields a
typed `PipelineEvent` (`app/services/events.py`) as each stage completes. It
owns its own DB session and runs the blocking agent work off the event loop
(`asyncio.to_thread`).

* `GET /api/analyses/{id}/stream?token=…` forwards those events to the browser as
  Server-Sent Events (the access token is a query param because `EventSource`
  cannot set an `Authorization` header — same trade-off as the localStorage
  tokens, see AUTH.md).
* `POST /api/analyses/{id}/run` still schedules a fire-and-forget background task
  that simply drains the generator, for non-streaming clients.

| Stage / status | Agent | Input | Output |
|-------|-------|-------|--------|
| `feature_extraction` | agent1 | product description (+ image → vision) | features, components, interfaces, knowledge analysis |
| `patent_search` | patent_search | agent1 features | top-5 `PatentHit`s: PatentsView → Google Patents → Tavily → concept stubs |
| `analysis` | agent2 Prosecutor | product + retrieved patents | claim-element mappings, risky claims, per-patent confidence |
| `analysis` | agent3 Defender | invention + patents + prosecutor mappings | distinctions, prior-art gaps, weak elements |
| `design_generation` | agent4 Design Engineer | product + prosecutor + defender | exactly 3 design-around alternatives |
| — | risk_matrix | all of the above (deterministic, no LLM) | per-element scores + overall risk |
| `report` | report_agent | everything above | executive summary, key risks, uncertainties, next steps, attorney questions + fixed disclaimer |
| — | image_genration | agent4 alternatives + `design_generation_prompt` | before/after DALL-E images — best-effort, streamed after the report so it never blocks text; skipped with a `IMAGE_GENERATION_SKIPPED` event when no image key is configured |
| `completed` | — | — | `completed_at` set, `PIPELINE_COMPLETED` emitted |

Each stage's full validated output is stored in `agent_runs.output_data`
(`agent_type` is now an unconstrained string — migration `202609010002`); the
API assembles `GET /api/analyses/{id}` from those rows, so a partial or failed
run is still inspectable and a page reload rehydrates without re-running.
Denormalized rows (`product_features`, `patents`, `design_alternatives`,
`risk_scores`) are written for convenience. On any exception the analysis is
marked `failed`, the true failing stage + message is recorded on an
`agent_runs` row, and an `ERROR` event is emitted.

Generated concept images are written under `MEDIA_ROOT` (default
`backend/media/`) and served from `/media/...`; remote DALL-E URLs are
downloaded and re-hosted so they survive past their ~1 h expiry.

## Why in-process instead of four HTTP services

The original repo had four separate FastAPI servers wired by hand-rolled `httpx`
proxy chains, three different API key variable names, and two OpenAI API styles.
Consolidating into one authenticated backend removed the multi-port fragility,
let auth + per-user persistence wrap the whole flow, and made the pipeline
testable end-to-end with a fake provider. The standalone agent servers still
exist (`agentN/server.py`) for LAN / debugging use.

## Database

`GUID` and `JSONBType` (`backend/app/models/types.py`) are cross-dialect column
types: native `uuid`/`jsonb` on Postgres, `CHAR(32)`/`JSON` on SQLite. This lets
local dev and the test suite run on SQLite with zero setup while production uses
Postgres + Alembic migrations.

## Data contracts

Each agent package owns its Pydantic schema (`agentN/schemas.py` or `models.py`)
— these are the JSON contracts between stages and are unchanged from the
original design. The backend has its own request/response schemas in
`backend/app/schemas/`.

## Tests

| Area | Location | Notes |
|------|----------|-------|
| provider layer | `llm/tests/` | registry, config precedence, error mapping, structured-output repair, streaming |
| agents 1–4 | `agentN/tests/` | prompts + contracts against `FakeProvider` |
| patent search | `patent_search/tests/` | source parsers, fallback order, dedupe, ranking, offline stubs (fake HTTP client) |
| report agent | `report_agent/tests/` | passthrough assembly, fixed disclaimer, deterministic fallback when the LLM fails |
| auth | `backend/tests/test_auth.py` | register/login/refresh/logout, token-type + version checks |
| authorization | `backend/tests/test_authorization.py` | anonymous rejection + cross-user 404s |
| orchestration | `backend/tests/test_pipeline.py` | full pipeline run + failure path, all on SQLite + FakeProvider |
| streaming | `backend/tests/test_stream.py` | SSE event ordering + count, query-token auth (401 without a valid token) |
