from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.community_watch.service import get_community_watch_snapshot
from app.modules.newsletter.schemas import NewsletterSubscribeIn
from app.modules.newsletter.service import NewsletterService


router = APIRouter()


@router.post("/newsletter/subscribe")
def newsletter_subscribe(payload: NewsletterSubscribeIn, db: Session = Depends(get_db)) -> dict:
    data = NewsletterService(db).subscribe(payload)
    return success(data.model_dump())


@router.post("/newsletter/send-digest")
def newsletter_send_digest(db: Session = Depends(get_db)) -> dict:
    snapshot = get_community_watch_snapshot()
    data = NewsletterService(db).send_daily_digest(snapshot)
    return success(data.model_dump())
