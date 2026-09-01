# Agent 1 — Feature Extractor + Knowledge Analysis

Two LLM jobs:

1. **Feature extraction** — from a product description (+ optional image):
   product summary, components, technical features (each tagged
   `user_stated` / `image_observation` / `assumption` with a confidence),
   interfaces, mechanisms, materials, software features, assumptions.
2. **Knowledge analysis** — the extracted features vs. concepts the model
   already knows: `similar_known_concepts`, an overall `similarity_score`, and a
   `disclaimer` that this is **not** a verified patent search.

No web search, no patent database, no fabricated patent numbers. If job 2 fails,
job 1's result is still returned with `status="analysis_failed"`.

## Usage

```python
from agent1 import run_agent1

out = run_agent1("A water bottle that senses liquid temperature ...", image_path=None)
```

CLI:

```bash
python -m agent1.main "A smart water bottle ..." [--image photo.png]
```

Standalone dev server:

```bash
uvicorn agent1.server:app --reload --port 8001
```

## Configuration

Provider/model from the shared config — see
[`../docs/PROVIDERS.md`](../docs/PROVIDERS.md). Optional override:
`AGENT1_LLM_PROVIDER`, `AGENT1_LLM_MODEL`.

## Contract

`agent1/schemas.py` — `Agent1Output`.

## Tests

```bash
python -m pytest -q agent1
```
