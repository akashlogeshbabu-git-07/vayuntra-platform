from starlette.middleware.base import BaseHTTPMiddleware
import uuid
class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.request_id = str(uuid.uuid4())
        return await call_next(request)
