import time
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger()

class LoggingAndTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # Extract metadata
        ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request start
        logger.info(
            "request_start",
            method=request.method,
            path=request.url.path,
            ip=ip,
            user_agent=user_agent
        )
        
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            logger.info(
                "request_success",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=round(process_time, 4)
            )
            return response
            
        except Exception as e:
            process_time = time.perf_counter() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_seconds=round(process_time, 4),
                exc_info=True
            )
            return Response(
                content="Internal Server Error",
                status_code=500
            )
