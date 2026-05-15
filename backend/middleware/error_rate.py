"""ASGI middleware that records every response status into the observability service."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from services import observability_service as obs


class ErrorRateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            response: Response = await call_next(request)
            obs.record(response.status_code)
            return response
        except Exception as e:
            obs.record(500)
            obs.capture_exception(e, context={"path": str(request.url.path), "method": request.method})
            raise
