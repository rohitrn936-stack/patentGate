import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from models import (
    ProsecutorRequest,
    ProsecutorOutput,
)

from agent import (
    analyze_product,
    stream_analysis,
)


app = FastAPI(
    title="PatentGate Prosecutor Agent",
    description="Agent 2 - Adversarial Patent Analysis",
    version="1.0.0",
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "ok",
        "agent": "prosecutor",
        "model": "gemini-3.7-flash",
        "streaming": True,
    }


# ============================================================
# NORMAL ANALYSIS
# ============================================================

@app.post(
    "/analyze",
    response_model=ProsecutorOutput,
)
def analyze(request: ProsecutorRequest):

    try:

        result = analyze_product(
            request.product,
            request.patents,
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# STREAMING ANALYSIS
# ============================================================

@app.post("/analyze/stream")
def analyze_stream(request: ProsecutorRequest):

    def event_generator():

        try:

            # START EVENT
            yield (
                "event: status\n"
                "data: "
                + json.dumps({
                    "status": "started",
                    "agent": "prosecutor",
                })
                + "\n\n"
            )

            # GEMINI STREAM
            for event in stream_analysis(
                request.product,
                request.patents,
            ):

                event_type = event["type"]

                # TOKEN
                if event_type == "token":

                    yield (
                        "event: token\n"
                        "data: "
                        + json.dumps({
                            "text": event["text"],
                        })
                        + "\n\n"
                    )

                # FINAL RESULT
                elif event_type == "result":

                    yield (
                        "event: result\n"
                        "data: "
                        + json.dumps(
                            event["data"]
                        )
                        + "\n\n"
                    )

                # ERROR
                elif event_type == "error":

                    yield (
                        "event: error\n"
                        "data: "
                        + json.dumps({
                            "error": event["error"],
                        })
                        + "\n\n"
                    )

            # COMPLETE
            yield (
                "event: complete\n"
                "data: "
                + json.dumps({
                    "status": "completed",
                })
                + "\n\n"
            )

        except Exception as error:

            yield (
                "event: error\n"
                "data: "
                + json.dumps({
                    "error": str(error),
                })
                + "\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )