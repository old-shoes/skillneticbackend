from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.track.schemas import TrackEventIn
from app.modules.track.service import create_track_event, validate_track_event


router = APIRouter()


@router.post("/track/event")
def track_event(payload: TrackEventIn, db: Session = Depends(get_db)) -> dict:
    try:
        validate_track_event(payload)
        create_track_event(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return success()
