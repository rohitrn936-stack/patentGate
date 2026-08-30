# PatentGate — Agent 4: Design-Around Engineer

Agent 4 receives the original product features (Agent 1), the Prosecutor's
risky claim-element analysis (Agent 2), and the Defender's distinctions and
weaknesses (Agent 3). It produces **3 alternative engineering designs** that are
intended to reduce overlap with the identified risky patent claim elements.

Each alternative includes:

- A description of the modified design
- The risky claim element it changes or avoids
- How it differs from the original product
- The engineering tradeoff
- A rationale for why it may reduce overlap
- A DALL-E-style image generation prompt

> **IMPORTANT:** Agent 4 is engineering/design guidance, **NOT legal advice**.
> It never claims that a design is "patent safe" or guarantees no infringement.

---

## 1. Install dependencies

Run these commands from the `agent4` directory in a Windows PowerShell terminal:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure `.env`

Copy the example and set your API key:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

```
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-5-nano
```

> Never commit `.env`. It is already listed in `.gitignore`.

## 3. Start the server

```powershell
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

## 4. API endpoints

### `GET /health`

```
http://127.0.0.1:8000/health
```

Response:

```json
{
  "status": "ok",
  "agent": "design-engineer",
  "model": "gpt-5-nano"
}
```

### `POST /design`

```
http://127.0.0.1:8000/design
```

This is the primary endpoint. It accepts `product`, `prosecutor`, and
`defender` together in a single request, calls the LLM, validates the result,
saves it to `output/design_output.json`, and returns it as JSON.

### `POST /design/stream`

```
http://127.0.0.1:8000/design/stream
```

Streaming version using Server-Sent Events (SSE) with
`Content-Type: text/event-stream`.

## 5. Example request for `POST /design`

```json
{
  "product": {
    "name": "Example Fraud Detection Platform",
    "description": "A platform that analyzes user transactions and generates fraud risk scores.",
    "features": [
      "Analyzes user transaction behavior",
      "Detects suspicious financial transactions",
      "Uses historical transaction data",
      "Generates a fraud risk score"
    ]
  },
  "prosecutor": {
    "risk_claims": [
      {
        "patent_id": "US345678",
        "claim_id": "Claim 1",
        "risk_level": "High",
        "reason": "The claim generates a risk score from historical transaction information."
      }
    ],
    "claim_element_mappings": [
      {
        "patent_id": "US345678",
        "claim_id": "Claim 1",
        "claim_element": "Calculating a risk score based on historical information",
        "product_feature": "Generates a fraud risk score",
        "strength": "High",
        "explanation": "Direct mapping."
      }
    ],
    "confidence_per_patent": [
      {
        "patent_id": "US345678",
        "confidence": 0.92,
        "explanation": "Direct mapping to historical data and risk-score generation."
      }
    ]
  },
  "defender": {
    "distinctions": [
      {
        "patent_id": "US345678",
        "claim_id": "Claim 1",
        "distinction": "Alternative architecture does not calculate a numerical risk score."
      }
    ],
    "prior_art_gaps": [],
    "weak_claim_elements": [
      {
        "patent_id": "US345678",
        "claim_id": "Claim 1",
        "claim_element": "Calculating a risk score",
        "weakness": "The product could use rule-based classifications instead of a numerical score."
      }
    ]
  }
}
```

## 6. Example response

```json
{
  "agent": "design-engineer",
  "status": "completed",
  "alternatives": [
    {
      "id": 1,
      "description": "Detailed description of the alternative engineering design.",
      "avoids_claim_element": "The specific risky claim element this design changes or avoids.",
      "changes_from_original": ["Change 1", "Change 2"],
      "tradeoff": "Engineering advantages and disadvantages.",
      "why_it_differs": "Why this design differs from the identified claim element.",
      "risk_reduction_rationale": "How this change may reduce overlap with the claim.",
      "design_generation_prompt": "Detailed prompt for generating an engineering concept image."
    },
    { "id": 2, "...": "..." },
    { "id": 3, "...": "..." }
  ],
  "legal_disclaimer": "These engineering alternatives are not a determination of patent infringement or freedom to operate. Legal review by a qualified patent attorney is required."
}
```

## 7. How Agent 2 (Prosecutor) communicates with Agent 4

Agent 2 sends its analysis output as the `prosecutor` field via an HTTP POST to
`/design`. There is no direct Python import between agents — only JSON over HTTP.

```python
requests.post(
    "http://127.0.0.1:8000/design",
    json={
        "product": {...},
        "prosecutor": <agent2_output_json>,
        "defender": <agent3_output_json>
    }
)
```

## 8. How Agent 3 (Defender) communicates with Agent 4

Agent 3 sends its output as the `defender` field in the same JSON request.
Agents 2 and 3 may each POST their JSON to Agent 4 separately (and Agent 4 can
be assembled with `product`, `prosecutor`, and `defender`), but the primary
integration is a single combined `POST /design` request.

## 9. Streaming (`/design/stream`)

The streaming endpoint emits Server-Sent Events:

```
event: status
data: {"status":"started","agent":"design-engineer"}

event: token
data: {"text":"..."}

event: result
data: {FINAL JSON}

event: complete
data: {"status":"completed"}
```

On error, an `event: error` with `data: {"error":"..."}` is emitted. If the LLM
cannot stream structured JSON safely, the raw text is streamed as `token`
events and the validated final structured JSON is sent as the `result` event.

## 10. Test with `test_agent4.py`

First make sure the server is running (see step 3), then run:

```powershell
python test_agent4.py
```

It loads `input/product.json`, `input/prosecutor.json`, and
`input/defender.json`, POSTs them to `/design`, prints the status code and
response JSON, and confirms `output/design_output.json` was created.

## 11. Legal disclaimer

Agent 4 produces engineering/design guidance only. It is **not** a
determination of patent infringement or freedom to operate. All outputs require
review by a qualified patent attorney. The agent deliberately avoids any
language that claims a design is "patent safe" or guarantees non-infringement.