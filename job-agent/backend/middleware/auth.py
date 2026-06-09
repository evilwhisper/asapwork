import secrets
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware
from backend.config import AUTH_ENABLED, ADMIN_USER, ADMIN_PASS_HASH

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

OPEN_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not AUTH_ENABLED:
            return await call_next(request)

        if request.url.path in OPEN_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return JSONResponse(
                {"detail": "Authentication required"},
                status_code=401,
                headers={"WWW-Authenticate": "Basic realm=\"Job Agent\""},
            )

        import base64
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not (
            secrets.compare_digest(username, ADMIN_USER)
            and ADMIN_PASS_HASH
            and pwd_context.verify(password, ADMIN_PASS_HASH)
        ):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return await call_next(request)
