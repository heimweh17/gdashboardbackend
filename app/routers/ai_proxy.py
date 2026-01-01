import requests
import logging
from fastapi import APIRouter, Request, HTTPException
from app.core.config import settings

router = APIRouter()
log = logging.getLogger("proxy_ai")

@router.post("/insights")
async def proxy_ai_insights(request: Request):
    if not settings.ai_service_url:
        raise HTTPException(status_code=500, detail="AI_SERVICE_URL not set")

    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    payload = await request.json()

    # Correlation ID: read from middleware (fallback to header)
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")

    headers = {"Authorization": auth_header}
    if rid:
        headers["X-Request-ID"] = rid

    url = f"{settings.ai_service_url}/ai/insights"
    log.info("Forwarding AI request", extra={"request_id": rid, "url": url})

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
    except Exception as e:
        log.exception("AI service unreachable", extra={"request_id": rid})
        raise HTTPException(status_code=502, detail=f"AI service unreachable: {e}")

    if r.status_code >= 400:
        log.warning(
            "AI service error",
            extra={"request_id": rid, "status_code": r.status_code, "body": r.text[:1000]},
        )
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()
