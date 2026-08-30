# PatentGate — Agent 3 (Defender)

Agent 3 is the **Defender** in the multi-agent patent analysis pipeline:

```
Agent 1 (Feature Extractor)  →  Agent 2 (Prosecutor)  →  Agent 3 (Defender)  →  Agent 4 (Design Engineer)
    :8001                          :8002                    :8003                    :8004
```

Agent 3 receives Agent 2's JSON (claim elements + prior-art information) and
produces a structured **defense analysis** that Agent 4 will consume.

> Agent 3 performs **no** new patent search. It reasons only over the
> prior-art information supplied by Agent 2, using the OpenAI API.

## Purpose

Given the claimed invention and prior-art concepts identified upstream, Agent 3:

1. Identifies **distinctions** between the claimed invention and prior art.
2. Identifies **prior-art gaps** — areas prior art appears not to cover.
3. Identifies **weak claim elements** that may be challenged.
4. Explains the reasoning behind each finding.
5. Produces structured JSON for Agent 4.

It **never** claims to have performed a verified patent search, never fabricates
patents, and never gives legal advice.

## Input JSON

Agent 2 POSTs its output to Agent 3. The body may be either the raw Agent 2 JSON
or wrapped under `agent2_output`. Agent 3 tolerantly extracts the payload:

```json
{
  "invention": "...",
  "claim_elements": [
    { "id": "C1", "element": "..." }
  ],
  "prior_art": [
    { "id": "PA1", "title": "...", "description": "...", "similarity": 0.7 }
  ],
  "prior_art_concepts": [
    { "name": "...", "similarity": 0.5 }
  ]
}
```

## Output JSON

```json
{
  "status": "ok",
  "errors": [],
  "defense_analysis": {
    "distinctions": [
      { "claim_element": "...", "distinction": "...", "reasoning": "..." }
    ],
    "prior_art_gaps": [
      { "claim_element": "...", "gap": "...", "reasoning": "..." }
    ],
    "weak_claim_elements": [
      { "claim_element": "...", "reasoning": "...", "risk": "medium" }
    ],
    "overall_assessment": "...",
    "confidence": 0.7,
    "disclaimer": "This is an AI-based analysis and is NOT a verified patent search or legal opinion."
  }
}
```

`risk` is one of `low`, `medium`, `high`. `confidence` is a number from `0.0`
to `1.0`.

## Endpoints

### `GET /health`

```bash
curl http://127.0.0.1:8003/health
```

Returns:

```json
{ "status": "ok" }
```

### `POST /analyze`

```bash
curl -X POST http://127.0.0.1:8003/analyze \
  -H "Content-Type: application/json" \
  -d @agent2_output.json
```

## Installing dependencies

```bash
cd patentGate/agent3
python3 -m venv .venv          # or reuse the project .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy the template and fill in the real value:

```bash
cp .env.example .env
```

| Variable         | Required | Description                                      |
| ---------------- | -------- | ------------------------------------------------ |
| `OPENAI_API_KEY` | yes      | OpenAI key for the Defender's LLM                |
| `OPENAI_MODEL`   | optional | Model ID (default `gpt-4o-mini` when unset)     |

`.env` is git-ignored — never commit it. The API key is never hard-coded.

## Starting the server

From the `agent3` directory:

```bash
uvicorn server:app --reload --port 8003
```

From the `patentGate` directory:

```bash
uvicorn agent3.server:app --reload --port 8003
```

## How agents connect

- **Agent 2 → Agent 3**: Agent 2 POSTs its JSON to
  `http://<MAC_IP>:8003/analyze`.
- **Agent 3 → Agent 4**: Agent 4 will later POST to its own `:8004/analyze`
  and consume Agent 3's `defense_analysis` JSON directly.

## Tests

```bash
cd patentGate/agent3
python -m pytest -q
```

Tests mock the OpenAI API and never make real API calls.