# PatentGate — Agent 1

PatentGate analyzes a user's product and helps identify potentially relevant
prior-art concepts. This repository currently contains **only Agent 1**:

> User input (text + optional image) → technical feature extraction (OpenAI)
> → knowledge-based similar-concept analysis (OpenAI) → validated structured
> JSON.

Agents 2 (Prosecutor), 3 (Defender), 4 (Design Engineer), the risk matrix and
the final report are **not** part of this repo yet.

## What Agent 1 does

**Job 1 — Technical feature extraction (OpenAI).** Given a product description
and an optional product image it extracts product name/summary, components,
technical features (each with id, name, description, component, function,
evidence, `evidence_source`, confidence), mechanisms, sensors, electronics,
materials, communication interfaces, software features and assumptions. Every
feature is labelled as one of:

- `user_stated` — explicitly stated by the user;
- `image_observation` — a characteristic actually visible in the image;
- `assumption` — a reasonable engineering guess (also listed under `assumptions`).

Agent 1 **never** invents specifications and **never** makes legal conclusions
(e.g. that a product infringes or does not infringe a patent).

**Job 2 — Knowledge-based similar-concept analysis (OpenAI).** The extracted
features are analyzed against concepts, technologies, and mechanisms the model
already knows from its training. The result is a structured
`KnowledgeAnalysis`:

- `invention` — a short summary of the invention;
- `technical_features` — the salient technical features;
- `similar_known_concepts` — each with name, why it is similar, matching
  features, differences, and a similarity score;
- `similarity_score` — 0.0 (no similarity) to 1.0 (near-identical);
- `similarity_explanation` — an overall explanation;
- `potentially_overlapping_areas` — domains likely to overlap;
- `confidence` — how sure the model is of the analysis;
- `disclaimer` — explicitly states the analysis is based on learned knowledge
  and is **NOT** a verified patent search.

> Agent 1 performs NO web search, NO Google Search grounding, and NO external
> patent retrieval. It never claims a real patent was found and never
> fabricates patent numbers, publication numbers, URLs, or dates.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
pip install -r requirements.txt
```

A `.venv` already exists in this project and the dependencies are installed.

## Required environment variables

Copy the template and fill in the real values:

```bash
cp .env.example .env
```

| Variable         | Required | Description                                        |
| ---------------- | -------- | -------------------------------------------------- |
| `OPENAI_API_KEY` | yes      | OpenAI key for feature extraction + analysis       |
| `OPENAI_MODEL`   | optional | OpenAI model ID (default `gpt-4o-mini`)            |

`.env` is git-ignored — never commit it. `OPENAI_MODEL` must be an actual model
ID exposed by the OpenAI API (not the ChatGPT display name).

## How to run the CLI

```bash
python main.py "Create a water bottle that measures the temperature of the \
liquid using a sensor in the cap and sends the temperature to a smartphone \
using Bluetooth."

# with an optional image (PNG or JPG)
python main.py "Smart measuring bottle" --image photos/bottle.png

# no argument: prompted interactively
python main.py
```

The structured JSON is printed to stdout.

## Example output structure

```json
{
  "status": "ok",
  "errors": [],
  "product": { "name": "...", "summary": "..." },
  "components": [ { "id": "C1", "name": "...", "description": "...", "function": "..." } ],
  "features": [
    {
      "id": "F1",
      "name": "Temperature sensor in the cap",
      "description": "...",
      "component": "cap",
      "function": "...",
      "evidence": "User stated ...",
      "evidence_source": "user_stated",
      "confidence": 1.0
    }
  ],
  "technical_concepts": [],
  "mechanisms": [],
  "materials": [],
  "interfaces": [ { "name": "Bluetooth", "interface_type": "wireless", "protocol": "Bluetooth", "description": "..." } ],
  "software_features": [],
  "assumptions": [],
  "analysis": {
    "invention": "...",
    "technical_features": ["Temperature sensor in the cap"],
    "similar_known_concepts": [
      {
        "name": "Smart beverage container with temperature sensing",
        "why_similar": "...",
        "matching_features": ["Temperature sensor in the cap"],
        "differences": "...",
        "similarity_score": 0.85
      }
    ],
    "similarity_score": 0.75,
    "similarity_explanation": "...",
    "potentially_overlapping_areas": ["smart drinkware"],
    "confidence": 0.7,
    "disclaimer": "This analysis is based on the model's learned knowledge and is NOT a verified patent search."
  }
}
```

## Architecture

```
patentGate/
├── agent1/
│   ├── __init__.py      # run_agent1() orchestrator + final validation
│   ├── extractor.py     # OpenAI: feature extraction + knowledge analysis
│   └── schemas.py       # Pydantic models (the JSON contract)
├── tests/
│   └── test_agent1.py
├── main.py              # CLI demo
├── requirements.txt
├── .env / .env.example
└── README.md
```

## Running the tests

Tests never hit the network and never use real API keys — OpenAI calls are
mocked.

```bash
python -m pytest -q
```

## Current limitations

- The similar-concept analysis is a knowledge-based aid, **not** legal advice
  and **not** a verified patent search. It is based purely on the model's
  learned knowledge.
- `OPENAI_MODEL` defaults to `gpt-4o-mini` only when the variable is unset;
  swap it if your account does not have access to that model.
- Only PNG, JPG and JPEG images are supported.
- A product image alone (no text description) is not accepted.