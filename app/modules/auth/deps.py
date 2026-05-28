from fastapi import Header, Request

from app.core.config import settings


def get_session_token(
    request: Request,
    authorization: str = Header(default="", alias="Authorization"),
) -> str:
    cookie_token = (request.cookies.get(settings.session_cookie_name) or "").strip()
    if cookie_token:
        return cookie_token
    return authorization[len("Bearer "):].strip() if authorization.startswith("Bearer ") else authorization.strip()
