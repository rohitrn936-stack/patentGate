import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from models import (
    ProsecutorRequest,
    ProsecutorOutput
)

from agent import (
    analyze_product,
    stream_analysis
)


app = FastAPI(
    title="PatentGate Prosecutor Agent",
    description="Agent 2 - Adversarial Patent Analysis",
    version="1.0.0"
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "ok",
        "agent": "prosecutor",
        "model": "gpt-5-nano",
        "streaming": True
    }


# ============================================================
# NORMAL ANALYSIS
# ============================================================

@app.post(
    "/analyze",
    response_model=ProsecutorOutput
)
def analyze(request: ProsecutorRequest):

    try:

        product = request.product.model_dump()

        patents = [
            patent.model_dump()
            for patent in request.patents
        ]

        result = analyze_product(
            product,
            patents
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# STREAMING ANALYSIS
# ============================================================

@app.post("/analyze/stream")
def analyze_stream(request: ProsecutorRequest):

    product = request.product.model_dump()

    patents = [
        patent.model_dump()
        for patent in request.patents
    ]


    def event_generator():

        try:

            # ------------------------------------------------
            # START EVENT
            # ------------------------------------------------

            yield (
                "event: status\n"
                "data: "
                + json.dumps({
                    "status": "started",
                    "agent": "prosecutor"
                })
                + "\n\n"
            )


            # ------------------------------------------------
            # STREAM GPT OUTPUT
            # ------------------------------------------------

            for event in stream_analysis(
                product,
                patents
            ):

                event_type = event["type"]


                # --------------------------------------------
                # TOKEN
                # --------------------------------------------

                if event_type == "token":

                    yield (
                        "event: token\n"
                        "data: "
                        + json.dumps({
                            "text": event["text"]
                        })
                        + "\n\n"
                    )


                # --------------------------------------------
                # FINAL STRUCTURED RESULT
                # --------------------------------------------

                elif event_type == "result":

                    yield (
                        "event: result\n"
                        "data: "
                        + json.dumps(
                            event["data"]
                        )
                        + "\n\n"
                    )


                # --------------------------------------------
                # ERROR
                # --------------------------------------------

                elif event_type == "error":

                    yield (
                        "event: error\n"
                        "data: "
                        + json.dumps({
                            "error": event["error"]
                        })
                        + "\n\n"
                    )


            # ------------------------------------------------
            # COMPLETE EVENT
            # ------------------------------------------------

            yield (
                "event: complete\n"
                "data: "
                + json.dumps({
                    "status": "completed"
                })
                + "\n\n"
            )


        except Exception as error:

            yield (
                "event: error\n"
                "data: "
                + json.dumps({
                    "error": str(error)
                })
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