import base64
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.auth.deps import get_session_token
from app.modules.auth.service import AuthService


router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads" / "skill-covers"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/svg+xml": ".svg"}


class UploadImageIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mimeType: str = Field(min_length=1, max_length=80)
    contentBase64: str = Field(min_length=1)


@router.post("/upload/skill-cover")
async def upload_skill_cover(
    payload: UploadImageIn,
    request: Request,
    token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> dict:
    del request
    AuthService(db).get_current_user(token)
    if payload.mimeType not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="unsupported image type")
    try:
        content = base64.b64decode(payload.contentBase64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid image payload") from exc
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="file too large")
    filename = f"{uuid4().hex}{ALLOWED_TYPES[payload.mimeType]}"
    target = UPLOAD_DIR / filename
    target.write_bytes(content)
    return success({"url": f"http://localhost:8000/uploads/skill-covers/{filename}"})
