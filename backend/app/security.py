"""Authentication, authorization, and bounded in-process request throttling."""

from __future__ import annotations

import hmac
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

logger = logging.getLogger("uvicorn.error")
bearer = HTTPBearer(auto_error=False)


class Role(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"


@dataclass(frozen=True)
class Principal:
    subject: str
    role: Role


def audit_security_event(event: str, **fields: object) -> None:
    """Emit a structured security event without request bodies or credentials."""
    logger.info(json.dumps({"event": event, **fields}, separators=(",", ":"), default=str))


def authenticate(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if not settings.security_is_configured:
        audit_security_event("authentication.configuration_error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend security is not configured",
        )

    token = (
        credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
    )
    principal: Principal | None = None
    if hmac.compare_digest(token, settings.backend_operator_token or ""):
        principal = Principal(subject="service-operator", role=Role.OPERATOR)
    elif hmac.compare_digest(token, settings.backend_viewer_token or ""):
        principal = Principal(subject="service-viewer", role=Role.VIEWER)

    if principal is None:
        audit_security_event(
            "authentication.denied",
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.principal = principal
    return principal


AuthenticatedPrincipal = Annotated[Principal, Depends(authenticate)]


def require_operator(request: Request, principal: AuthenticatedPrincipal) -> Principal:
    if principal.role is not Role.OPERATOR:
        audit_security_event(
            "authorization.denied",
            request_id=getattr(request.state, "request_id", None),
            subject=principal.subject,
            required_role=Role.OPERATOR,
            path=request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role required",
        )
    return principal


OperatorPrincipal = Annotated[Principal, Depends(require_operator)]


class SlidingWindowLimiter:
    """Thread-safe local limiter. Deployment docs describe its per-instance boundary."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, int(window_seconds - (now - timestamps[0])) + 1)
                return False, retry_after
            timestamps.append(now)
            return True, 0

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = SlidingWindowLimiter()


def enforce_rate_limit(
    request: Request,
    principal: AuthenticatedPrincipal,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    is_write = request.method not in {"GET", "HEAD", "OPTIONS"}
    limit = settings.rate_limit_write_requests if is_write else settings.rate_limit_read_requests
    scope = "write" if is_write else "read"
    allowed, retry_after = rate_limiter.allow(
        f"{principal.subject}:{scope}",
        limit=limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    if not allowed:
        audit_security_event(
            "rate_limit.denied",
            request_id=getattr(request.state, "request_id", None),
            subject=principal.subject,
            scope=scope,
            path=request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    return principal


RateLimitedPrincipal = Annotated[Principal, Depends(enforce_rate_limit)]
