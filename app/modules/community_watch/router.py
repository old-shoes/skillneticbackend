from fastapi import APIRouter

from app.core.response import success
from app.modules.community_watch.fetcher import refresh_community_watch_snapshot
from app.modules.community_watch.service import get_community_watch_snapshot


router = APIRouter()


@router.get("/community-watch")
def community_watch() -> dict:
    data = get_community_watch_snapshot()
    return success(data.model_dump())


@router.post("/community-watch/refresh")
def community_watch_refresh() -> dict:
    return success(refresh_community_watch_snapshot())
