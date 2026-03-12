from starlette.middleware.base import BaseHTTPMiddleware
class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)
