# app/core/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

def _new_id() -> str:
    return uuid.uuid4().hex

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or _new_id()
        request.state.request_id = rid

        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response
