"""ASGI middleware: record every response status + latency for observability + Prometheus."""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from services import observability_service as obs
from services import metrics_service as metrics


class ErrorRateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        path = str(request.url.path)
        method = request.method
        try:
            response: Response = await call_next(request)
            duration = time.perf_counter() - start
            obs.record(response.status_code)
            metrics.observe_request(method, path, response.status_code, duration)
            return response
        except Exception as e:
            duration = time.perf_counter() - start
            obs.record(500)
            metrics.observe_request(method, path, 500, duration)
            obs.capture_exception(e, context={"path": path, "method": method})
            raise
