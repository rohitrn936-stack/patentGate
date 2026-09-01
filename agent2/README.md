# Agent 2 — Prosecutor

Adversarial patent analysis. Given product features (Agent 1) and a set of
patents, the Prosecutor argues where the patents' claim elements *could
potentially* read on the product. It uses cautious language, never states that
infringement exists, and never invents patent data.

> Replaces the old `prosecutor-agent/` scripts with an importable package.

## Usage

```python
from agent2 import Prosecutor

out = Prosecutor().analyze(product_dict, patents_list)   # -> ProsecutorOutput
for event in Prosecutor().stream(product_dict, patents_list):
    ...  # {"type": "token"|"result"|"error", ...}
```

Standalone dev server (`/analyze`, `/analyze/stream`):

```bash
uvicorn agent2.server:app --reload --port 8002
```

## Configuration

Provider/model from the shared config — see
[`../docs/PROVIDERS.md`](../docs/PROVIDERS.md). Optional override:
`AGENT2_LLM_PROVIDER`, `AGENT2_LLM_MODEL`.

## Contract

`agent2/schemas.py` — `ProsecutorRequest` (`product`, `patents[1..25]`) in;
`ProsecutorOutput` (`risk_claims[]`, `claim_element_mappings[]`,
`confidence_per_patent[]`) out.

## Tests

```bash
python -m pytest -q agent2
```
