import json

from fastapi import HTTPException

from app.modules.community_watch.fetcher import get_snapshot_path, refresh_community_watch_snapshot
from app.modules.community_watch.schemas import CommunityWatchSnapshot


def get_community_watch_snapshot() -> CommunityWatchSnapshot:
    file_path = get_snapshot_path()
    if not file_path.exists():
        try:
            refresh_community_watch_snapshot()
        except Exception as exc:
            raise HTTPException(status_code=404, detail="community watch snapshot not found and refresh failed") from exc

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return CommunityWatchSnapshot.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="community watch snapshot is not valid json") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to load community watch snapshot") from exc
