from __future__ import annotations

import logging
import threading
from datetime import datetime, time, timedelta, timezone

from app.core.database import SessionLocal
from app.core.config import settings
from app.modules.community_watch.fetcher import refresh_community_watch_snapshot
from app.modules.community_watch.schemas import CommunityWatchSnapshot
from app.modules.newsletter.service import NewsletterService


logger = logging.getLogger(__name__)

_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _local_timezone() -> timezone:
    return timezone(timedelta(hours=settings.community_watch_timezone_offset_hours))


def _seconds_until_next_run() -> float:
    now_utc = datetime.now(timezone.utc)
    local_tz = _local_timezone()
    now_local = now_utc.astimezone(local_tz)
    scheduled_time = time(
        hour=settings.community_watch_refresh_hour_local,
        minute=settings.community_watch_refresh_minute_local,
    )
    next_run_local = datetime.combine(now_local.date(), scheduled_time, tzinfo=local_tz)
    if next_run_local <= now_local:
        next_run_local += timedelta(days=1)
    return max(60.0, (next_run_local.astimezone(timezone.utc) - now_utc).total_seconds())


def _send_digest_safely(snapshot: dict) -> None:
    if not settings.newsletter_daily_digest_enabled:
        return
    db = SessionLocal()
    try:
        result = NewsletterService(db).send_daily_digest(CommunityWatchSnapshot.model_validate(snapshot))
        logger.info("Newsletter digest sent: delivered=%s skipped=%s", result.delivered, result.skipped)
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to send newsletter digest: %s", exc)
    finally:
        db.close()


def _refresh_safely(reason: str) -> None:
    try:
        logger.info("Refreshing community watch snapshot: %s", reason)
        snapshot = refresh_community_watch_snapshot()
        if reason == "daily-schedule":
            _send_digest_safely(snapshot)
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to refresh community watch snapshot: %s", exc)


def _run_scheduler_loop() -> None:
    if settings.community_watch_refresh_on_startup:
        _refresh_safely("startup")

    while not _stop_event.wait(_seconds_until_next_run()):
        _refresh_safely("daily-schedule")


def start_community_watch_scheduler() -> None:
    global _scheduler_thread
    if not settings.community_watch_scheduler_enabled:
        logger.info("Community watch scheduler is disabled")
        return
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_run_scheduler_loop,
        name="community-watch-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()
    logger.info(
        "Community watch scheduler started, next refresh runs daily at %02d:%02d (UTC%+d)",
        settings.community_watch_refresh_hour_local,
        settings.community_watch_refresh_minute_local,
        settings.community_watch_timezone_offset_hours,
    )


def stop_community_watch_scheduler() -> None:
    _stop_event.set()
