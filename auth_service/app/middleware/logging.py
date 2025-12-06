from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        logger.info(f"→ {request.method} {request.url.path}")
        
        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"← {request.method} {request.url.path} "
            f"[{response.status_code}] {process_time:.2f}s"
        )
        
        return response
