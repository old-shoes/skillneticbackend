from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import string
import ssl
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode
from urllib import error as urllib_error
from urllib import request as urllib_request

import certifi
from fastapi import HTTPException, Request
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.me.engagement import PointService
from app.modules.auth.models import AuthEmailCode, AuthLog, PasswordResetRecord, User, UserAuthAccount, UserSession
from app.modules.auth.schemas import (
    AuthActionOut,
    AuthEmailCodeSendIn,
    AuthEmailCodeSendOut,
    AuthGithubLoginOut,
    AuthEmailLoginIn,
    AuthEmailRegisterIn,
    AuthLoginIn,
    AuthPasswordChangeIn,
    AuthPasswordResetIn,
    AuthRegisterIn,
    AuthSessionOut,
    UserOut,
)


SESSION_DAYS = 30
SHORT_SESSION_DAYS = 14
REMEMBER_SESSION_DAYS = 30
EMAIL_CODE_TTL_MINUTES = 10
EMAIL_CODE_COOLDOWN_SECONDS = 60
EMAIL_CODE_HOURLY_LIMIT = 20
EMAIL_CODE_DAILY_LIMIT = 20


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_email_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _email_code_subject(scene: str) -> str:
    if scene == "forgot_password":
        return "skillnetic.ai 重置密码验证码 / Password Reset Code"
    return "skillnetic.ai 注册验证码 / Registration Code"


def _email_code_html(scene: str, code: str) -> str:
    scene_label = "重置密码" if scene == "forgot_password" else "注册账号"
    action_label = "重置密码" if scene == "forgot_password" else "完成注册"
    action_label_en = "reset your password" if scene == "forgot_password" else "complete your sign up"
    return f"""
<div style="margin:0;background:#f8fafc;padding:32px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#0f172a;">
  <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:24px;overflow:hidden;box-shadow:0 18px 48px rgba(15,23,42,0.08);">
    <div style="padding:28px 32px;background:linear-gradient(135deg,#eff6ff 0%,#f8fafc 100%);border-bottom:1px solid #e2e8f0;">
      <div style="font-size:13px;letter-spacing:0.12em;text-transform:uppercase;font-weight:700;color:#2563eb;">skillnetic.ai</div>
      <div style="margin-top:10px;font-size:28px;line-height:1.25;font-weight:800;color:#0f172a;">验证码 Verification Code</div>
      <div style="margin-top:10px;font-size:15px;line-height:1.7;color:#475569;">
        你正在进行{scene_label}，请使用下面的 6 位验证码完成操作。<br />
        Use this 6-digit code to {action_label_en}.
      </div>
    </div>
    <div style="padding:32px;">
      <div style="text-align:center;margin-bottom:20px;">
        <div style="display:inline-block;padding:14px 22px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:16px;font-size:32px;font-weight:800;letter-spacing:8px;color:#2563eb;">
          {code}
        </div>
      </div>
      <div style="font-size:15px;line-height:1.8;color:#334155;">
        验证码 10 分钟内有效，请尽快完成{action_label}。<br />
        This code expires in 10 minutes.
      </div>
      <div style="margin-top:16px;padding:14px 16px;border-radius:14px;background:#f8fafc;border:1px solid #e2e8f0;font-size:14px;line-height:1.7;color:#475569;">
        如果这不是你本人发起的请求，可以直接忽略这封邮件。<br />
        If you did not request this code, you can safely ignore this email.
      </div>
    </div>
    <div style="padding:18px 32px;border-top:1px solid #e2e8f0;background:#ffffff;font-size:13px;line-height:1.7;color:#64748b;">
      This email was sent by skillnetic.ai
    </div>
  </div>
</div>
""".strip()


def _email_code_text(scene: str, code: str) -> str:
    scene_label = "重置密码" if scene == "forgot_password" else "注册账号"
    action_label_cn = "重置密码" if scene == "forgot_password" else "完成注册"
    action_label_en = "reset your password" if scene == "forgot_password" else "complete your sign up"
    return (
        f"skillnetic.ai 验证码\n"
        f"你正在进行{scene_label}，验证码：{code}\n"
        f"请在 10 分钟内使用该验证码完成{action_label_cn}。\n\n"
        f"skillnetic.ai verification code: {code}\n"
        f"This code expires in 10 minutes and can be used to {action_label_en}."
    )


def _build_default_nickname(email: str) -> str:
    local_part = (email.split("@", 1)[0] or "user").strip()
    cleaned = "".join(char for char in local_part if char.isalnum() or char in ("_", "-"))
    base = cleaned[:24] or "user"
    return f"user_{base}"


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _github_connected(self, user_id) -> bool:
        account = self.db.scalar(
            select(UserAuthAccount).where(
                UserAuthAccount.user_id == user_id,
                UserAuthAccount.provider == "github",
            )
        )
        return account is not None

    def _to_user_out(self, user: User) -> UserOut:
        return UserOut(
            id=str(user.id),
            email=user.email,
            nickname=user.nickname,
            avatarUrl=user.avatar_url,
            githubConnected=user.github_connected or self._github_connected(user.id),
            level=user.level,
            locale=user.locale,
            createdAt=user.created_at,
        )

    def _create_session(
        self,
        user: User,
        request: Optional[Request],
        *,
        session_days: int = SESSION_DAYS,
    ) -> AuthSessionOut:
        token = secrets.token_urlsafe(32)
        session = UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            user_agent=request.headers.get("user-agent") if request else None,
            ip=request.client.host if request and request.client else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=session_days),
        )
        self.db.add(session)
        return AuthSessionOut(token=token, user=self._to_user_out(user))

    def _after_login_success(self, user: User, request: Optional[Request], *, award_daily_points: bool = False) -> None:
        point_service = PointService(self.db)
        point_service.update_last_login(
            user_id=user.id,
            ip=self._request_ip(request),
        )
        if award_daily_points:
            point_service.award_daily_login_points(user.id)

    def _request_ip(self, request: Optional[Request]) -> Optional[str]:
        return request.client.host if request and request.client else None

    def _request_user_agent(self, request: Optional[Request]) -> Optional[str]:
        return request.headers.get("user-agent") if request else None

    def _log_event(
        self,
        event_type: str,
        *,
        request: Optional[Request],
        user_id=None,
        email: Optional[str] = None,
        provider: Optional[str] = None,
        success: bool = True,
        fail_reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.db.add(
            AuthLog(
                user_id=user_id,
                event_type=event_type,
                provider=provider,
                email=email,
                ip=self._request_ip(request),
                user_agent=self._request_user_agent(request),
                success=success,
                fail_reason=fail_reason,
                metadata_json=metadata or {},
            )
        )

    def _normalize_email(self, email: str) -> str:
        return email.lower().strip()

    def _assert_password_strength(self, password: str) -> None:
        value = password.strip()
        if len(value) < 8 or len(value) > 80:
            raise HTTPException(status_code=400, detail="password must be 8-80 characters")
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise HTTPException(status_code=400, detail="password must include letters and numbers")

    def _revoke_sessions(self, user_id, *, exclude_token_hash: Optional[str] = None) -> None:
        now = datetime.now(timezone.utc)
        sessions = self.db.scalars(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
        ).all()
        for session in sessions:
            if exclude_token_hash and session.token_hash == exclude_token_hash:
                continue
            session.revoked_at = now
            self.db.add(session)

    def _latest_email_code_query(self, email: str, scene: str) -> Select:
        return (
            select(AuthEmailCode)
            .where(
                AuthEmailCode.email == email,
                AuthEmailCode.scene == scene,
            )
            .order_by(AuthEmailCode.created_at.desc())
        )

    def _state_signature(self, value: str) -> str:
        return hmac.new(
            settings.auth_state_secret.encode("utf-8"),
            value.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_github_state(self, intent: str) -> str:
        nonce = secrets.token_urlsafe(16)
        raw = f"{intent}:{nonce}"
        signature = self._state_signature(raw)
        payload = f"{raw}:{signature}"
        return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")

    def _parse_github_state(self, encoded_state: str) -> str:
        try:
            decoded = base64.urlsafe_b64decode(encoded_state.encode("utf-8")).decode("utf-8")
            intent, nonce, signature = decoded.split(":", 2)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid github state") from exc

        raw = f"{intent}:{nonce}"
        expected = self._state_signature(raw)
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=400, detail="invalid github state")
        if intent not in ("login", "register"):
            raise HTTPException(status_code=400, detail="invalid github intent")
        return intent

    def _github_request_json(self, url: str, *, data: Optional[dict] = None, access_token: str = "") -> dict:
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {
            "Accept": "application/json",
            "User-Agent": "skillnetic-auth/1.0",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        request_obj = urllib_request.Request(
            url,
            data=body,
            headers=headers,
            method="POST" if body is not None else "GET",
        )
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        try:
            with urllib_request.urlopen(request_obj, timeout=10, context=ssl_context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:400]
            raise HTTPException(status_code=502, detail=f"github oauth request failed: {detail or exc.reason}") from exc
        except urllib_error.URLError as exc:
            raise HTTPException(status_code=502, detail="failed to connect to github oauth service") from exc

    def _ensure_github_config(self) -> None:
        if not settings.github_client_id.strip() or not settings.github_client_secret.strip():
            raise HTTPException(status_code=503, detail="github oauth is not configured")

    def github_login_url(self, intent: str) -> AuthGithubLoginOut:
        self._ensure_github_config()
        state = self._build_github_state(intent)
        query = urlencode(
            {
                "client_id": settings.github_client_id,
                "redirect_uri": settings.github_callback_url,
                "scope": "read:user user:email",
                "state": state,
            }
        )
        return AuthGithubLoginOut(url=f"https://github.com/login/oauth/authorize?{query}")

    def _bind_github_account(self, user: User, github_user: dict, primary_email: str) -> None:
        existing = self.db.scalar(
            select(UserAuthAccount).where(
                UserAuthAccount.provider == "github",
                UserAuthAccount.provider_user_id == str(github_user["id"]),
            )
        )
        now = datetime.now(timezone.utc)
        user.github_connected = True
        self.db.add(user)
        if existing is not None:
            existing.user_id = user.id
            existing.email = primary_email
            existing.github_username = github_user.get("login")
            existing.github_avatar_url = github_user.get("avatar_url")
            existing.github_profile_url = github_user.get("html_url")
            existing.is_verified = True
            existing.last_used_at = now
            self.db.add(existing)
            return

        self.db.add(
            UserAuthAccount(
                user_id=user.id,
                provider="github",
                provider_user_id=str(github_user["id"]),
                email=primary_email,
                github_username=github_user.get("login"),
                github_avatar_url=github_user.get("avatar_url"),
                github_profile_url=github_user.get("html_url"),
                is_primary=False,
                is_verified=True,
                last_used_at=now,
            )
        )

    def _send_email_via_resend(self, *, to_email: str, scene: str, code: str) -> None:
        if not settings.resend_api_key.strip():
            return

        payload = {
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": _email_code_subject(scene),
            "html": _email_code_html(scene, code),
            "text": _email_code_text(scene, code),
        }
        if settings.resend_reply_to.strip():
            payload["reply_to"] = settings.resend_reply_to

        req = urllib_request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ai-skill-auth/1.0",
            },
            method="POST",
        )
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        try:
            with urllib_request.urlopen(req, timeout=10, context=ssl_context) as response:
                status_code = getattr(response, "status", 200)
                if status_code >= 400:
                    raise HTTPException(status_code=502, detail="email provider rejected the verification email")
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:400]
            raise HTTPException(
                status_code=502,
                detail=f"failed to send verification email via resend: {detail or exc.reason}",
            ) from exc
        except urllib_error.URLError as exc:
            raise HTTPException(status_code=502, detail="failed to connect to resend email service") from exc

    def send_email_code(self, payload: AuthEmailCodeSendIn, request: Optional[Request]) -> AuthEmailCodeSendOut:
        email = self._normalize_email(payload.email)
        now = datetime.now(timezone.utc)
        latest = self.db.scalar(self._latest_email_code_query(email, payload.scene))
        if latest is not None:
            latest_created_at = latest.created_at
            if latest_created_at.tzinfo is None:
                latest_created_at = latest_created_at.replace(tzinfo=timezone.utc)
            seconds_since_last = int((now - latest_created_at).total_seconds())
            if seconds_since_last < EMAIL_CODE_COOLDOWN_SECONDS:
                raise HTTPException(
                    status_code=400,
                    detail=f"please wait {EMAIL_CODE_COOLDOWN_SECONDS - seconds_since_last}s before requesting another code",
                )

        ip = self._request_ip(request)
        hourly_window = now - timedelta(hours=1)
        daily_window = now - timedelta(days=1)
        hourly_count = len(
            self.db.scalars(
                select(AuthEmailCode).where(
                    AuthEmailCode.send_ip == ip,
                    AuthEmailCode.created_at >= hourly_window,
                )
            ).all()
        )
        daily_count = len(
            self.db.scalars(
                select(AuthEmailCode).where(
                    AuthEmailCode.email == email,
                    AuthEmailCode.created_at >= daily_window,
                )
            ).all()
        )
        if hourly_count >= EMAIL_CODE_HOURLY_LIMIT:
            raise HTTPException(status_code=429, detail="too many verification code requests from this IP")
        if daily_count >= EMAIL_CODE_DAILY_LIMIT:
            raise HTTPException(status_code=429, detail="too many verification code requests for this email")

        code = "".join(secrets.choice(string.digits) for _ in range(6))
        email_code = AuthEmailCode(
            email=email,
            scene=payload.scene,
            code_hash=hash_email_code(code),
            status="unused",
            send_ip=ip,
            user_agent=self._request_user_agent(request),
            expires_at=now + timedelta(minutes=EMAIL_CODE_TTL_MINUTES),
        )
        self.db.add(email_code)
        self._log_event(
            "email_code_send",
            request=request,
            email=email,
            provider="email",
            metadata={"scene": payload.scene},
        )
        self._send_email_via_resend(to_email=email, scene=payload.scene, code=code)
        self.db.commit()
        return AuthEmailCodeSendOut(
            cooldownSeconds=EMAIL_CODE_COOLDOWN_SECONDS,
            debugCode=code if settings.app_env != "production" else None,
        )

    def github_callback(self, code: str, state: str, request: Optional[Request]) -> AuthSessionOut:
        self._ensure_github_config()
        intent = self._parse_github_state(state)
        token_payload = self._github_request_json(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_callback_url,
            },
        )
        access_token = token_payload.get("access_token", "")
        if not access_token:
            raise HTTPException(status_code=400, detail="github oauth access token missing")

        github_user = self._github_request_json("https://api.github.com/user", access_token=access_token)
        github_emails = self._github_request_json("https://api.github.com/user/emails", access_token=access_token)

        primary_email = ""
        if isinstance(github_emails, list):
            primary = next((item for item in github_emails if item.get("primary") and item.get("verified")), None)
            fallback = next((item for item in github_emails if item.get("verified")), None)
            primary_email = (primary or fallback or {}).get("email", "")

        primary_email = self._normalize_email(primary_email)
        if not primary_email:
            raise HTTPException(status_code=400, detail="github verified email is unavailable")

        github_account = self.db.scalar(
            select(UserAuthAccount).where(
                UserAuthAccount.provider == "github",
                UserAuthAccount.provider_user_id == str(github_user["id"]),
            )
        )
        user = self.db.get(User, github_account.user_id) if github_account is not None else None
        if user is None:
            user = self.db.scalar(select(User).where(User.email == primary_email, User.deleted_at.is_(None)))

        created = False
        if user is None:
            user = User(
                email=primary_email,
                password_hash=hash_password(secrets.token_urlsafe(24)),
                nickname=github_user.get("login") or _build_default_nickname(primary_email),
                avatar_url=github_user.get("avatar_url"),
                email_verified=True,
                github_connected=True,
                locale="zh",
                is_active=True,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            created = True

        if user.avatar_url != github_user.get("avatar_url"):
            user.avatar_url = github_user.get("avatar_url")
        user.email_verified = True
        user.github_connected = True
        self.db.add(user)

        self._bind_github_account(user, github_user, primary_email)
        session = self._create_session(user, request)
        self._after_login_success(user, request)
        event_type = "github_register_success" if created and intent == "register" else "github_login_success"
        self._log_event(
            event_type,
            request=request,
            email=primary_email,
            provider="github",
            user_id=user.id,
            metadata={"intent": intent, "githubLogin": github_user.get("login")},
        )
        self.db.commit()
        return session

    def _consume_email_code(self, email: str, scene: str, code: str) -> AuthEmailCode:
        normalized_email = self._normalize_email(email)
        now = datetime.now(timezone.utc)
        email_code = self.db.scalar(
            select(AuthEmailCode).where(
                AuthEmailCode.email == normalized_email,
                AuthEmailCode.scene == scene,
                AuthEmailCode.status == "unused",
            ).order_by(AuthEmailCode.created_at.desc())
        )
        if email_code is None:
            raise HTTPException(status_code=400, detail="verification code not found")
        expires_at = email_code.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            email_code.status = "expired"
            self.db.add(email_code)
            self.db.commit()
            raise HTTPException(status_code=400, detail="verification code expired")
        if email_code.code_hash != hash_email_code(code.strip()):
            raise HTTPException(status_code=400, detail="verification code invalid")
        email_code.status = "used"
        email_code.used_at = now
        self.db.add(email_code)
        return email_code

    def register(self, payload: AuthRegisterIn, request: Optional[Request]) -> AuthSessionOut:
        email = self._normalize_email(payload.email)
        existing = self.db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
        if existing is not None:
            raise HTTPException(status_code=400, detail="email already registered")
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            nickname=_build_default_nickname(email),
            email_verified=True,
            github_connected=False,
            locale=payload.locale.strip() or "zh",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.add(
            UserAuthAccount(
                user_id=user.id,
                provider="email",
                email=email,
                password_hash=user.password_hash,
                is_primary=True,
                is_verified=True,
            )
        )
        session = self._create_session(user, request)
        self._after_login_success(user, request)
        self._log_event("email_register_success", request=request, email=email, provider="email", user_id=user.id)
        self.db.commit()
        return session

    def login(self, payload: AuthLoginIn, request: Optional[Request]) -> AuthSessionOut:
        email = self._normalize_email(payload.email)
        user = self.db.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None), User.is_active.is_(True))
        )
        if user is None or user.password_hash != hash_password(payload.password):
            self._log_event(
                "email_login_failed",
                request=request,
                email=email,
                provider="email",
                success=False,
                fail_reason="invalid_email_or_password",
            )
            self.db.commit()
            raise HTTPException(status_code=400, detail="invalid email or password")
        session = self._create_session(user, request)
        self._after_login_success(user, request)
        self._log_event("email_login_success", request=request, email=email, provider="email", user_id=user.id)
        self.db.commit()
        return session

    def register_email(self, payload: AuthEmailRegisterIn, request: Optional[Request]) -> AuthSessionOut:
        email = self._normalize_email(payload.email)
        if payload.password != payload.confirmPassword:
            raise HTTPException(status_code=400, detail="password confirmation does not match")
        if not payload.agreeTerms:
            raise HTTPException(status_code=400, detail="you must agree to the terms")
        self._assert_password_strength(payload.password)
        existing = self.db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
        if existing is not None:
            raise HTTPException(status_code=400, detail="email already registered")
        self._consume_email_code(email, "register", payload.emailCode)
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            nickname=_build_default_nickname(email),
            email_verified=True,
            github_connected=False,
            locale=payload.locale.strip() or "zh",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.db.add(
            UserAuthAccount(
                user_id=user.id,
                provider="email",
                email=email,
                password_hash=user.password_hash,
                is_primary=True,
                is_verified=True,
            )
        )
        session = self._create_session(user, request)
        self._after_login_success(user, request)
        self._log_event("email_register_success", request=request, email=email, provider="email", user_id=user.id)
        self.db.commit()
        return session

    def login_email(self, payload: AuthEmailLoginIn, request: Optional[Request]) -> AuthSessionOut:
        email = self._normalize_email(payload.email)
        user = self.db.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None), User.is_active.is_(True))
        )
        if user is None or user.password_hash != hash_password(payload.password):
            self._log_event(
                "email_login_failed",
                request=request,
                email=email,
                provider="email",
                success=False,
                fail_reason="invalid_email_or_password",
            )
            self.db.commit()
            raise HTTPException(status_code=400, detail="invalid email or password")
        session = self._create_session(
            user,
            request,
            session_days=REMEMBER_SESSION_DAYS if payload.rememberMe else SHORT_SESSION_DAYS,
        )
        self._after_login_success(user, request)
        self._log_event("email_login_success", request=request, email=email, provider="email", user_id=user.id)
        self.db.commit()
        return session

    def _get_or_create_test_user(self) -> User:
        user = self.db.scalar(
            select(User).where(
                User.email == settings.test_auth_email,
                User.deleted_at.is_(None),
            )
        )
        if user is not None:
            if not user.is_active:
                user.is_active = True
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
            return user

        user = User(
            email=settings.test_auth_email,
            password_hash=hash_password(settings.test_auth_token),
            nickname="Test User",
            github_connected=False,
            locale="zh",
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_current_user(self, token: str) -> User:
        if not token:
            raise HTTPException(status_code=401, detail="unauthorized")
        if token == settings.test_auth_token:
            return self._get_or_create_test_user()
        session = self.db.scalar(
            select(UserSession).where(
                UserSession.token_hash == hash_token(token),
                UserSession.revoked_at.is_(None),
            )
        )
        if session is None or session.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="unauthorized")
        user = self.db.get(User, session.user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            raise HTTPException(status_code=401, detail="unauthorized")
        return user

    def get_current_user_optional(self, token: str) -> Optional[User]:
        if not token:
            return None
        try:
            return self.get_current_user(token)
        except HTTPException:
            return None

    def me(self, token: str) -> UserOut:
        return self._to_user_out(self.get_current_user(token))

    def logout(self, token: str, request: Optional[Request]) -> AuthActionOut:
        if not token:
            raise HTTPException(status_code=401, detail="unauthorized")
        if token == settings.test_auth_token:
            raise HTTPException(status_code=403, detail="test auth session cannot log out")
        session = self.db.scalar(
            select(UserSession).where(
                UserSession.token_hash == hash_token(token),
                UserSession.revoked_at.is_(None),
            )
        )
        if session is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        session.revoked_at = datetime.now(timezone.utc)
        self.db.add(session)
        self._log_event("logout", request=request, user_id=session.user_id)
        self.db.commit()
        return AuthActionOut()

    def reset_password(self, payload: AuthPasswordResetIn, request: Optional[Request]) -> AuthActionOut:
        email = self._normalize_email(payload.email)
        if payload.newPassword != payload.confirmPassword:
            raise HTTPException(status_code=400, detail="password confirmation does not match")
        self._assert_password_strength(payload.newPassword)
        user = self.db.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None), User.is_active.is_(True))
        )
        if user is None:
            raise HTTPException(status_code=400, detail="email not registered")
        if user.password_hash == hash_password(payload.newPassword):
            raise HTTPException(status_code=400, detail="new password must be different from the current password")
        email_code = self._consume_email_code(email, "forgot_password", payload.emailCode)
        user.password_hash = hash_password(payload.newPassword)
        self.db.add(user)
        self._revoke_sessions(user.id)
        self.db.add(
            PasswordResetRecord(
                user_id=user.id,
                email=email,
                email_code_id=email_code.id,
                reset_ip=self._request_ip(request),
                user_agent=self._request_user_agent(request),
                success=True,
            )
        )
        self._log_event("password_reset_success", request=request, email=email, provider="email", user_id=user.id)
        self.db.commit()
        return AuthActionOut()

    def change_password(self, token: str, payload: AuthPasswordChangeIn, request: Optional[Request]) -> AuthActionOut:
        if token == settings.test_auth_token:
            raise HTTPException(status_code=403, detail="test auth session cannot change password")
        if payload.newPassword != payload.confirmPassword:
            raise HTTPException(status_code=400, detail="password confirmation does not match")
        self._assert_password_strength(payload.newPassword)
        user = self.get_current_user(token)
        if user.password_hash != hash_password(payload.currentPassword):
            raise HTTPException(status_code=400, detail="current password is incorrect")
        if payload.currentPassword == payload.newPassword:
            raise HTTPException(status_code=400, detail="new password must be different from the current password")
        user.password_hash = hash_password(payload.newPassword)
        self.db.add(user)
        self._revoke_sessions(user.id)
        self._log_event("password_change_success", request=request, email=user.email, provider="email", user_id=user.id)
        self.db.commit()
        return AuthActionOut()
