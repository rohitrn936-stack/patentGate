# Agent 3 — Defender

Consumes Agent 2's (Prosecutor's) output and produces a structured **defense
analysis**: distinctions between the claimed invention and the prior art,
prior-art gaps, and weak claim elements. It performs **no** new patent search
and never gives legal advice.

## Usage

Agent 3 runs through the shared provider-agnostic LLM layer and is orchestrated
in-process by the backend pipeline.

```python
from agent3.agent import Defender

analysis = Defender().analyze(agent2_output_dict)   # -> DefenseAnalysis
```

Standalone dev server:

```bash
uvicorn agent3.server:app --reload --port 8003
```

`POST /analyze` accepts either Agent 2's raw JSON or `{ "agent2_output": {...} }`.

## Configuration

Provider/model come from the shared config — see
[`../docs/PROVIDERS.md`](../docs/PROVIDERS.md). Optional per-agent override:
`AGENT3_LLM_PROVIDER`, `AGENT3_LLM_MODEL`.

## Contract

`agent3/schemas.py` — `DefenseAnalysis` (`distinctions[]`, `prior_art_gaps[]`,
`weak_claim_elements[]` with `risk ∈ {low, medium, high}`, `overall_assessment`,
`confidence`, `disclaimer`), wrapped in `DefenderResponse`.

## Tests

```bash
python -m pytest -q agent3
```

Tests use the in-memory `FakeProvider` — no network, no key.
