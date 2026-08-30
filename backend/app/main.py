from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import verify_database_connection
from app.routes import analyses, auth, products, agent1


settings = get_settings()

app = FastAPI(title="PatentGate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(analyses.router)
app.include_router(agent1.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict[str, str]:
    try:
        await verify_database_connection()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database connection failed") from exc
    return {"status": "ok", "database": "connected"}
