from __future__ import annotations

import json
import re
import ssl
from datetime import datetime, timezone
from html import escape
from urllib import error as urllib_error
from urllib import request as urllib_request

import certifi
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.community_watch.schemas import CommunityWatchSnapshot
from app.modules.newsletter.models import NewsletterSubscriber
from app.modules.newsletter.schemas import NewsletterDigestSendOut, NewsletterSubscribeIn, NewsletterSubscribeOut


EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


class NewsletterService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _normalize_email(self, email: str) -> str:
        value = email.strip().lower()
        if not EMAIL_RE.match(value):
            raise HTTPException(status_code=400, detail="invalid email")
        return value

    def subscribe(self, payload: NewsletterSubscribeIn) -> NewsletterSubscribeOut:
        email = self._normalize_email(payload.email)
        locale = (payload.locale or "zh").strip().lower()[:20] or "zh"
        source = (payload.source or "footer").strip().lower()[:50] or "footer"

        subscriber = self.db.scalar(select(NewsletterSubscriber).where(NewsletterSubscriber.email == email))
        if subscriber:
            if subscriber.status == "active":
                return NewsletterSubscribeOut(email=email, subscribed=True, alreadySubscribed=True)

            subscriber.status = "active"
            subscriber.locale = locale
            subscriber.source = source
            subscriber.unsubscribed_at = None
            self.db.add(subscriber)
            self.db.commit()
            return NewsletterSubscribeOut(email=email, subscribed=True, alreadySubscribed=False)

        subscriber = NewsletterSubscriber(
            email=email,
            status="active",
            locale=locale,
            source=source,
        )
        self.db.add(subscriber)
        self.db.commit()
        return NewsletterSubscribeOut(email=email, subscribed=True, alreadySubscribed=False)

    def _active_subscribers(self) -> list[NewsletterSubscriber]:
        return self.db.scalars(
            select(NewsletterSubscriber).where(NewsletterSubscriber.status == "active").order_by(NewsletterSubscriber.created_at.asc())
        ).all()

    def _build_digest_subject(self, snapshot: CommunityWatchSnapshot) -> str:
        date_label = snapshot.meta.generatedAt[:10] if snapshot.meta.generatedAt else datetime.now(timezone.utc).date().isoformat()
        prefix = settings.newsletter_daily_digest_subject_prefix.strip() or "Skillnetic"
        return f"{prefix} GitHub 社区日报 · {date_label}"

    def _build_digest_html(self, snapshot: CommunityWatchSnapshot) -> str:
        repos = snapshot.repositories[:5]
        issues = snapshot.issues[:3]
        topics = snapshot.topics[:5]

        repo_html = "".join(
            f"""
            <li style="margin:0 0 14px;">
              <div style="font-weight:700;color:#0f172a;">{escape(repo.fullName)}</div>
              <div style="margin-top:4px;font-size:13px;color:#475569;">{escape((repo.descriptionZh or repo.description or '').strip())}</div>
              <div style="margin-top:6px;font-size:12px;color:#64748b;">Stars {escape(repo.starsLabel)} · Forks {escape(repo.forksLabel)}</div>
            </li>
            """
            for repo in repos
        )
        issue_html = "".join(
            f"""
            <li style="margin:0 0 12px;">
              <div style="font-weight:700;color:#0f172a;">{escape(issue.title)}</div>
              <div style="margin-top:4px;font-size:12px;color:#64748b;">{escape(issue.repository)} · {escape(issue.commentCountLabel)} 评论</div>
            </li>
            """
            for issue in issues
        )
        topic_html = "".join(
            f"""
            <li style="margin:0 0 10px;">
              <span style="font-weight:700;color:#0f172a;">#{escape(topic.name)}</span>
              <span style="font-size:12px;color:#64748b;"> · {escape(topic.repoCountLabel)} 个相关仓库</span>
            </li>
            """
            for topic in topics
        )

        return f"""
        <div style="margin:0;background:#f8fafc;padding:32px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#0f172a;">
          <div style="max-width:720px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:24px;overflow:hidden;box-shadow:0 18px 48px rgba(15,23,42,0.08);">
            <div style="padding:28px 32px;background:linear-gradient(135deg,#eff6ff 0%,#f8fafc 100%);border-bottom:1px solid #e2e8f0;">
              <div style="font-size:13px;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#2563eb;">Skillnetic Daily Digest</div>
              <div style="margin-top:10px;font-size:28px;line-height:1.25;font-weight:800;color:#0f172a;">今日 GitHub 社区热点</div>
              <div style="margin-top:10px;font-size:15px;line-height:1.7;color:#475569;">
                观察开源热点、挖选题、找竞品和追踪开发者讨论方向。
              </div>
            </div>
            <div style="padding:28px 32px;">
              <h3 style="margin:0 0 14px;font-size:18px;color:#0f172a;">热门仓库</h3>
              <ul style="padding-left:18px;margin:0 0 24px;">{repo_html}</ul>
              <h3 style="margin:0 0 14px;font-size:18px;color:#0f172a;">高热讨论</h3>
              <ul style="padding-left:18px;margin:0 0 24px;">{issue_html}</ul>
              <h3 style="margin:0 0 14px;font-size:18px;color:#0f172a;">Topic 榜单</h3>
              <ul style="padding-left:18px;margin:0;">{topic_html}</ul>
            </div>
          </div>
        </div>
        """.strip()

    def _build_digest_text(self, snapshot: CommunityWatchSnapshot) -> str:
        repo_lines = [
            f"- {repo.fullName} | {repo.descriptionZh or repo.description or ''} | Stars {repo.starsLabel}"
            for repo in snapshot.repositories[:5]
        ]
        issue_lines = [f"- {issue.title} | {issue.repository} | {issue.commentCountLabel} 评论" for issue in snapshot.issues[:3]]
        topic_lines = [f"- #{topic.name} | {topic.repoCountLabel} 个相关仓库" for topic in snapshot.topics[:5]]
        return "\n".join(
            [
                "今日 GitHub 社区热点",
                "",
                "热门仓库",
                *repo_lines,
                "",
                "高热讨论",
                *issue_lines,
                "",
                "Topic 榜单",
                *topic_lines,
            ]
        )

    def _send_email_via_resend(self, *, to_email: str, subject: str, html: str, text: str) -> None:
        if not settings.resend_api_key.strip():
            raise HTTPException(status_code=500, detail="resend_api_key is not configured")

        payload = {
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text,
        }
        if settings.resend_reply_to.strip():
            payload["reply_to"] = settings.resend_reply_to

        req = urllib_request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "skillnetic-newsletter/1.0",
            },
            method="POST",
        )
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        with urllib_request.urlopen(req, timeout=15, context=ssl_context):
            return

    def send_daily_digest(self, snapshot: CommunityWatchSnapshot) -> NewsletterDigestSendOut:
        subscribers = self._active_subscribers()
        subject = self._build_digest_subject(snapshot)
        html = self._build_digest_html(snapshot)
        text = self._build_digest_text(snapshot)

        delivered = 0
        skipped = 0
        for subscriber in subscribers:
            try:
                self._send_email_via_resend(
                    to_email=subscriber.email,
                    subject=subject,
                    html=html,
                    text=text,
                )
                delivered += 1
            except urllib_error.URLError:
                skipped += 1
            except urllib_error.HTTPError:
                skipped += 1

        return NewsletterDigestSendOut(
            subscribers=len(subscribers),
            delivered=delivered,
            skipped=skipped,
            subject=subject,
        )
