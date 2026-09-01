# Agent 4 — Design-Around Engineer

Given Agent 1 (product features), Agent 2 (Prosecutor) and Agent 3 (Defender)
outputs, Agent 4 proposes **3 alternative engineering designs** that aim to
reduce overlap with the risky claim elements.

> Engineering/design guidance only — **not** legal advice. It never claims a
> design is "patent safe" or guarantees non-infringement.

## Usage

Agent 4 runs through the shared provider-agnostic LLM layer. It is orchestrated
in-process by the backend pipeline; you rarely call it directly.

```python
from agent4 import DesignEngineer

out = DesignEngineer().generate(product_dict, prosecutor_dict, defender_dict)
```

Standalone dev server (SSE streaming at `/design/stream`, JSON at `/design`):

```bash
uvicorn agent4.server:app --reload --port 8004
```

## Configuration

No agent-specific keys. The provider/model come from the shared config — see
[`../docs/PROVIDERS.md`](../docs/PROVIDERS.md). Optional per-agent override:
`AGENT4_LLM_PROVIDER`, `AGENT4_LLM_MODEL`.

## Contract

`agent4/models.py` — `DesignRequest` in, `DesignOutput` out (`agent`, `status`,
`alternatives[3]`, `legal_disclaimer`). Each alternative: `id`, `description`,
`avoids_claim_element`, `changes_from_original[]`, `tradeoff`, `why_it_differs`,
`risk_reduction_rationale`, `design_generation_prompt`.

## Tests

```bash
python -m pytest -q agent4
```

Tests use the in-memory `FakeProvider` — no network, no key.
