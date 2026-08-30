============================================================
AGENT 2 INTEGRATION README
============================================================

Also create a separate documentation file:

AGENT2_INTEGRATION.md

This file is specifically for the developer/team member responsible for Agent 2 (Prosecutor).

The purpose of this document is to clearly explain how Agent 2 sends its output to Agent 4 over HTTP.

Write it for a beginner developer. Use simple explanations and copy-pasteable commands.

The documentation MUST contain the following:

------------------------------------------------------------
1. AGENT 4 URLS
------------------------------------------------------------

Explain that when Agent 4 is running locally:

Health:
GET http://127.0.0.1:8004/health

Main design endpoint:
POST http://127.0.0.1:8004/design

Streaming endpoint:
POST http://127.0.0.1:8004/design/stream

Explain that if Agent 2 is running on another computer, 127.0.0.1 will NOT work.

Instead Agent 2 must use the Agent 4 computer's LAN IPv4 address, for example:

http://172.18.11.215:8004/design

Clearly explain that the IP address must be replaced with the actual IP address of the computer running Agent 4.

------------------------------------------------------------
2. WHAT AGENT 2 SENDS
------------------------------------------------------------

Explain that Agent 2 sends JSON containing:

{
  "product": {...},
  "prosecutor": {...},
  "defender": {...}
}

Explain each field.

The prosecutor field contains Agent 2's output.

The defender field contains Agent 3's output.

The product field contains the original product features.

------------------------------------------------------------
3. COMPLETE EXAMPLE REQUEST
------------------------------------------------------------

Include a complete copy-pasteable JSON example:

{
  "product": {
    "name": "Example Fraud Detection Platform",
    "description": "A platform that detects suspicious financial transactions.",
    "features": [
      "Analyzes user transaction behavior",
      "Uses historical transaction data",
      "Detects suspicious transactions",
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
        "explanation": "The claim element directly maps to the product feature."
      }
    ],

    "confidence_per_patent": [
      {
        "patent_id": "US345678",
        "confidence": 0.92,
        "explanation": "Strong overlap with historical data and risk-score generation."
      }
    ]
  },

  "defender": {
    "distinctions": [
      {
        "patent_id": "US345678",
        "claim_id": "Claim 1",
        "distinction": "An alternative architecture does not calculate a numerical risk score."
      }
    ],

    "prior_art_gaps": [],

    "weak_claim_elements": [
      {
        "patent_id": "US345678",
        "claim_id": "Claim 1",
        "claim_element": "Calculating a risk score",
        "weakness": "The product could use categorical classifications instead."
      }
    ]
  }
}

------------------------------------------------------------
4. POSTMAN TEST
------------------------------------------------------------

Give exact beginner-friendly Postman instructions:

1. Start Agent 4.
2. Open Postman.
3. Create a new POST request.
4. Enter:

http://127.0.0.1:8004/design

5. Go to Body.
6. Select raw.
7. Select JSON.
8. Paste the example JSON.
9. Click Send.
10. Explain where the Agent 4 response appears.

Also explain that the response is JSON.

------------------------------------------------------------
5. PYTHON EXAMPLE FOR AGENT 2
------------------------------------------------------------

Provide a complete Python example showing how Agent 2 can send its output to Agent 4.

Use requests.

Example structure:

import requests

url = "http://127.0.0.1:8004/design"

payload = {
    "product": product_data,
    "prosecutor": prosecutor_output,
    "defender": defender_output
}

response = requests.post(
    url,
    json=payload,
    timeout=300
)

print(response.status_code)
print(response.json())

Explain exactly where Agent 2's existing output should be placed.

Do NOT hardcode example data when showing the real integration. Clearly identify the variables Agent 2 should replace.

------------------------------------------------------------
6. CURL EXAMPLE
------------------------------------------------------------

Provide a Windows PowerShell curl example that can be used for testing.

Make sure it works correctly in PowerShell.

------------------------------------------------------------
7. RESPONSE FROM AGENT 4
------------------------------------------------------------

Show an example of the response Agent 2 will receive:

{
  "agent": "design-engineer",
  "status": "completed",
  "alternatives": [
    {
      "id": 1,
      "description": "...",
      "avoids_claim_element": "...",
      "changes_from_original": [],
      "tradeoff": "...",
      "why_it_differs": "...",
      "risk_reduction_rationale": "...",
      "design_generation_prompt": "..."
    }
  ],
  "legal_disclaimer": "..."
}

Explain that Agent 2 does not need to understand or modify this response. Agent 4 produces it for the next stage of the pipeline.

------------------------------------------------------------
8. STREAMING
------------------------------------------------------------

Explain the streaming endpoint:

POST /design/stream

Explain that it uses Server-Sent Events (SSE).

Show the types of events:

event: status
event: token
event: result
event: complete
event: error

Explain that normal /design should be used if Agent 2 simply needs the final JSON.

Use /design/stream if the team wants live output while Agent 4 is processing.

------------------------------------------------------------
9. NETWORKING
------------------------------------------------------------

Clearly explain:

If Agent 2 and Agent 4 are on the SAME COMPUTER:

http://127.0.0.1:8004/design

If Agent 2 and Agent 4 are on DIFFERENT computers on the same Wi-Fi/LAN:

http://AGENT4_COMPUTER_IP:8004/design

Example:

http://172.18.11.215:8004/design

Explain that Agent 4 must be started with:

uvicorn server:app --reload --host 0.0.0.0 --port 8004

Explain that Windows Firewall may need to allow Python/Uvicorn to accept connections.

------------------------------------------------------------
10. TROUBLESHOOTING
------------------------------------------------------------

Include simple solutions for:

- Connection refused
- 404 Not Found
- 422 Validation Error
- 500 Internal Server Error
- Agent 4 not running
- Wrong IP address
- Different Wi-Fi networks
- JSON formatting errors
- Missing API key

For each error, explain what the developer should check.

------------------------------------------------------------
11. AGENT PIPELINE
------------------------------------------------------------

Include this architecture diagram in the README:

Agent 1
  |
  | Product Features JSON
  v
Patent Search
  |
  | Patent JSON
  v
Agent 2
  |
  | Prosecutor JSON
  v
Agent 3
  |
  | Defender JSON
  v
Agent 4
  |
  | 3 Design Alternatives JSON
  v
Final Report

Also explain that Agent 4 can receive the combined:

Product + Agent 2 + Agent 3

payload through:

POST /design

------------------------------------------------------------
12. SECURITY
------------------------------------------------------------

Explain:

- Never send OPENAI_API_KEY inside the JSON request.
- Never put the API key in GitHub.
- Never commit .env.
- Agent 2 only sends analysis data to Agent 4.
- API keys must remain in environment variables.

============================================================
FINAL REQUIREMENT
============================================================

After creating Agent 4, make sure these files exist:

server.py
agent.py
models.py
requirements.txt
.env.example
.gitignore
README.md
AGENT2_INTEGRATION.md
test_agent4.py

Also create the example JSON files required for testing.

Do not merely describe these files.

Actually create them in the project directory.

Before finishing, verify that the Python files have no syntax errors and that the FastAPI server can start successfully.