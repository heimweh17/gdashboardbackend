import requests
from fastapi import APIRouter, Request, HTTPException
from app.core.config import settings

router = APIRouter()

@router.post("/insights")
async def proxy_ai_insights(request: Request):
    if not settings.ai_service_url:
        raise HTTPException(status_code=500, detail="AI_SERVICE_URL not set")

    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    payload = await request.json()

    try:
        r = requests.post(
            f"{settings.ai_service_url}/ai/insights",
            json=payload,
            headers={"Authorization": auth_header},
            timeout=60,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service unreachable: {e}")

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()
