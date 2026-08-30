import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.schemas.agent1 import Agent1Request, Agent1Response

router = APIRouter(prefix="/api/agent1", tags=["agent1"])

settings = get_settings()


@router.post("", response_model=Agent1Response)
async def call_agent1(request: Agent1Request) -> Agent1Response:
    """Call Agent 1 server to analyze product description."""
    description = request.input.strip()
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product description is empty"
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.agent1_server_url}/analyze",
                json={"product_description": description}
            )
            
            if response.status_code != 200:
                return Agent1Response(
                    success=False,
                    error=f"Agent 1 server returned status {response.status_code}: {response.text}"
                )
            
            result = response.json()
            
            if result.get("status") == "error":
                return Agent1Response(
                    success=False,
                    error=result.get("error", "Agent 1 failed to process the request")
                )
            
            return Agent1Response(success=True, result=result)
            
    except httpx.ConnectError:
        return Agent1Response(
            success=False,
            error=f"Cannot connect to Agent 1 server. Make sure it's running on {settings.agent1_server_url}"
        )
    except httpx.TimeoutException:
        return Agent1Response(
            success=False,
            error="Agent 1 request timed out"
        )
    except Exception as exc:
        return Agent1Response(
            success=False,
            error=f"Agent 1 failed: {type(exc).__name__}"
        )