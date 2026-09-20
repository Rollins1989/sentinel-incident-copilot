"""Optional API-key guard for administrative endpoints."""
from __future__ import annotations

import secrets
from typing import Annotated
from fastapi import Depends, Header, HTTPException, status
from sentinel.config import settings

def require_admin_token(token: Annotated[str | None, Header(alias="X-Sentinel-Admin-Token")] = None) -> None:
    if not settings.admin_token:
        return
    if not token or not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrative token required.")

AdminGuard = Annotated[None, Depends(require_admin_token)]
