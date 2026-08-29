# ClaimBreaker — Agent 1: Feature Extractor

Agent 1 converts a product description and optional JPEG, PNG, or WebP image
into validated technical features for the Patent Search Layer. It calls
`gpt-5-nano` through the OpenAI Responses API. It does not search patents or
make legal conclusions.

## Use

```python
from claimbreaker import extract_features

result = extract_features("A smart helmet detects impacts and sends an alert.")
```

The result is a `FeatureExtractionResult` Pydantic model containing
`product_summary`, `domain`, atomic `features`, `search_terms`,
`technical_keywords`, and `uncertainties`.

## Optional image analysis

Create a local `.env` file and pass an image path to use OpenAI vision:

```bash
OPENAI_API_KEY="your_key"
# Optional; gpt-5-nano is the default
OPENAI_MODEL="gpt-5-nano"
```

```bash
.venv/bin/python -m claimbreaker.cli "A smart helmet detects impacts." --image ./helmet.png
```

Start the minimal FastAPI test endpoint with `uvicorn claimbreaker.api:app --reload`.
Send multipart form data to `POST /agent-1/extract`, using the
`product_description` and optional `image` fields.

```bash
.venv/bin/uvicorn claimbreaker.api:app --reload
```

## Local checks

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

## Patent Search Layer

The MVP queries the public Google Patents search site directly; it does not use
PatentsView, Tavily, or another search API/key. Send a validated Agent 1 result
to `POST /patents/search`, or run the sample end-to-end command:

```bash
.venv/bin/python -m claimbreaker.patent_cli
```

The search layer creates 3–5 focused technical queries, normalizes genuine
Google Patents candidates, deduplicates them, and returns at most five local
lexically ranked results. It does not make legal conclusions.
