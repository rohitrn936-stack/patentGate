import os
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from agent4.models import (
    DesignRequest,
    DesignOutput
)

from agent4.agent import (
    MODEL_NAME,
    client,
    generate_designs,
    stream_designs
)


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "design_output.json"

app = FastAPI(
    title="PatentGate Design-Around Engineer",
    description="Agent 4 - Alternative Design Generation",
    version="1.0.0"
)


def _check_api_key():
    if client.api_key is None:
        raise HTTPException(
            status_code=500,
            detail="Missing API key. Configure NVIDIA_API_KEY in your .env file."
        )


def _save_output(output: DesignOutput):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "agent": "design-engineer",
        "model": MODEL_NAME
    }


# ============================================================
# MAIN DESIGN ENDPOINT (accepts product + prosecutor + defender)
# ============================================================

@app.post(
    "/design",
    response_model=DesignOutput
)
def design(request: DesignRequest):
    try:
        _check_api_key()

        product = request.product.model_dump()
        prosecutor = request.prosecutor.model_dump()
        defender = request.defender.model_dump()

        result = generate_designs(product, prosecutor, defender)

        _save_output(result)

        return result

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# STREAMING DESIGN ENDPOINT (SSE)
# ============================================================

@app.post("/design/stream")
def design_stream(request: DesignRequest):
    product = request.product.model_dump()
    prosecutor = request.prosecutor.model_dump()
    defender = request.defender.model_dump()

    def event_generator():
        try:
            _check_api_key()

            yield (
                "event: status\n"
                "data: "
                + json.dumps({
                    "status": "started",
                    "agent": "design-engineer"
                })
                + "\n\n"
            )

            final_data = None

            for event in stream_designs(product, prosecutor, defender):

                event_type = event["type"]

                if event_type == "token":
                    yield (
                        "event: token\n"
                        "data: "
                        + json.dumps({"text": event["text"]})
                        + "\n\n"
                    )

                elif event_type == "result":
                    final_data = event["data"]

                    yield (
                        "event: result\n"
                        "data: "
                        + json.dumps(final_data)
                        + "\n\n"
                    )

                elif event_type == "error":
                    yield (
                        "event: error\n"
                        "data: "
                        + json.dumps({"error": event["error"]})
                        + "\n\n"
                    )

            if final_data is not None:
                try:
                    output = DesignOutput.model_validate(final_data)
                    _save_output(output)
                except Exception:
                    pass

            yield (
                "event: complete\n"
                "data: "
                + json.dumps({"status": "completed"})
                + "\n\n"
            )

        except HTTPException as error:
            yield (
                "event: error\n"
                "data: "
                + json.dumps({"error": error.detail})
                + "\n\n"
            )

        except Exception as error:
            yield (
                "event: error\n"
                "data: "
                + json.dumps({"error": str(error)})
                + "\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )