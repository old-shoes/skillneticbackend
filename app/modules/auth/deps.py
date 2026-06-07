from typing import Any, Optional

from fastapi import Header, Request

from app.core.config import settings


def get_session_token(
    request: Request,
    authorization: Optional[str] = Header(default="", alias="Authorization"),
) -> str:
    cookie_token = (request.cookies.get(settings.session_cookie_name) or "").strip()
    if cookie_token:
        return cookie_token
    raw_authorization: Any = authorization
    header_value = raw_authorization.strip() if isinstance(raw_authorization, str) else ""
    return header_value[len("Bearer "):].strip() if header_value.startswith("Bearer ") else header_value
