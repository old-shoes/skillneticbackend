from typing import Iterable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.modules.auth.service import AuthService
from app.modules.auth.deps import get_session_token
from app.core.database import get_db
from app.core.response import success
from app.modules.skill_submissions.schemas import (
    AdminSkillSubmissionQueryIn,
    SkillSubmissionApproveIn,
    SkillSubmissionDraftCreateIn,
    SkillSubmissionDraftIn,
    SkillSubmissionQueryIn,
    SkillSubmissionRejectIn,
    SkillSubmissionRequestRevisionIn,
    SkillSubmissionReviewDraftIn,
    SkillSubmissionSubmitIn,
    UserGithubSkillParseIn,
    UserGithubSkillSubmitIn,
)
from app.modules.skill_submissions.service import SkillSubmissionService
from app.modules.skill_submissions.service import DEFAULT_ADMIN_ID


user_router = APIRouter()
admin_router = APIRouter()

SUBMISSION_VIEW_ROLES = {"super_admin", "content_admin", "reviewer"}
SUBMISSION_CREATE_ROLES = {"super_admin", "content_admin"}
SUBMISSION_REVIEW_ROLES = {"super_admin", "content_admin", "reviewer"}
SUBMISSION_APPROVE_ROLES = {"super_admin", "content_admin"}
SUBMISSION_REJECT_ROLES = {"super_admin", "content_admin"}
SUBMISSION_REVISION_ROLES = {"super_admin", "content_admin", "reviewer"}


def require_submission_role(allowed_roles: Iterable[str]):
    allowed = set(allowed_roles)

    def dependency(x_admin_role: str = Header(default="content_admin", alias="X-Admin-Role")) -> str:
        role = (x_admin_role or "").strip()
        if role not in SUBMISSION_VIEW_ROLES:
            raise HTTPException(status_code=403, detail="forbidden")
        if role not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return role

    return dependency


def require_user_id(
    request: Request,
    token: str = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> str:
    del request
    user = AuthService(db).get_current_user(token)
    return str(user.id)


@user_router.post("/skill-submissions/draft")
def create_skill_submission_draft(
    payload: SkillSubmissionDraftCreateIn,
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).create_draft(payload, UUID(user_id))
    return success(data.model_dump())


@user_router.post("/user/skills/github/parse")
def parse_user_github_skill(
    payload: UserGithubSkillParseIn,
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    del user_id
    data = SkillSubmissionService(db).parse_user_github_skill(payload.github_url)
    return success(data.model_dump())


@user_router.post("/user/skills/github/submit")
def submit_user_github_skill(
    payload: UserGithubSkillSubmitIn,
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).submit_user_github_skill(payload, UUID(user_id))
    return success(data.model_dump())


@user_router.get("/skill-submissions/meta")
def get_skill_submission_meta(db: Session = Depends(get_db)) -> dict:
    data = SkillSubmissionService(db).get_meta()
    return success(data.model_dump())


@user_router.get("/skill-submissions/{submission_id}")
def get_skill_submission(
    submission_id: str,
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).get_submission(submission_id, UUID(user_id))
    return success(data.model_dump())


@user_router.patch("/skill-submissions/{submission_id}")
def update_skill_submission(
    submission_id: str,
    payload: SkillSubmissionDraftIn,
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).update_submission(submission_id, payload, UUID(user_id))
    return success(data.model_dump())


@user_router.post("/skill-submissions/{submission_id}/submit")
def submit_skill_submission(
    submission_id: str,
    payload: SkillSubmissionSubmitIn,
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).submit_submission(submission_id, payload, UUID(user_id))
    return success(data.model_dump())


@user_router.delete("/skill-submissions/{submission_id}")
def delete_skill_submission(
    submission_id: str,
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    SkillSubmissionService(db).delete_submission(submission_id, UUID(user_id))
    return success({"success": True})


@user_router.get("/my/skill-submissions")
def get_my_skill_submissions(
    status: str = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    user_id: str = Depends(require_user_id),
    db: Session = Depends(get_db),
) -> dict:
    query = SkillSubmissionQueryIn(status=status, page=page, pageSize=pageSize)
    data = SkillSubmissionService(db).list_my_submissions(query, UUID(user_id))
    return success(data.model_dump())


@admin_router.get("/skill-submissions")
def get_admin_skill_submissions(
    q: str = Query(default=None),
    status: str = Query(default=None),
    categoryId: str = Query(default=None),
    tag: str = Query(default=None),
    source: str = Query(default=None),
    submittedStart: str = Query(default=None),
    submittedEnd: str = Query(default=None),
    onlyPending: bool = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=50),
    _: str = Depends(require_submission_role(SUBMISSION_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    query = AdminSkillSubmissionQueryIn(
        q=q,
        status=status,
        categoryId=categoryId,
        tag=tag,
        source=source,
        submittedStart=submittedStart,
        submittedEnd=submittedEnd,
        onlyPending=onlyPending,
        page=page,
        pageSize=pageSize,
    )
    data = SkillSubmissionService(db).list_admin_submissions(query)
    return success(data.model_dump())


@admin_router.get("/skill-submissions/{submission_id}")
def get_admin_skill_submission_detail(
    submission_id: str,
    _: str = Depends(require_submission_role(SUBMISSION_VIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).get_admin_detail(submission_id)
    return success(data.model_dump())


@admin_router.post("/skill-submissions/draft")
def create_admin_skill_submission_draft(
    payload: SkillSubmissionDraftCreateIn,
    _: str = Depends(require_submission_role(SUBMISSION_CREATE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).create_draft(payload, DEFAULT_ADMIN_ID)
    return success(data.model_dump())


@admin_router.patch("/skill-submissions/{submission_id}")
def update_admin_skill_submission(
    submission_id: str,
    payload: SkillSubmissionDraftIn,
    _: str = Depends(require_submission_role(SUBMISSION_CREATE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).update_submission(submission_id, payload, DEFAULT_ADMIN_ID)
    return success(data.model_dump())


@admin_router.post("/skill-submissions/{submission_id}/submit")
def submit_admin_skill_submission(
    submission_id: str,
    payload: SkillSubmissionSubmitIn,
    _: str = Depends(require_submission_role(SUBMISSION_CREATE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).submit_submission(submission_id, payload, DEFAULT_ADMIN_ID)
    return success(data.model_dump())


@admin_router.post("/skill-submissions/{submission_id}/approve")
def approve_skill_submission(
    submission_id: str,
    payload: SkillSubmissionApproveIn,
    _: str = Depends(require_submission_role(SUBMISSION_APPROVE_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).approve(submission_id, payload)
    return success(data.model_dump())


@admin_router.post("/skill-submissions/{submission_id}/reject")
def reject_skill_submission(
    submission_id: str,
    payload: SkillSubmissionRejectIn,
    _: str = Depends(require_submission_role(SUBMISSION_REJECT_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).reject(submission_id, payload)
    return success(data.model_dump())


@admin_router.post("/skill-submissions/{submission_id}/request-revision")
def request_skill_submission_revision(
    submission_id: str,
    payload: SkillSubmissionRequestRevisionIn,
    _: str = Depends(require_submission_role(SUBMISSION_REVISION_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).request_revision(submission_id, payload)
    return success(data.model_dump())


@admin_router.post("/skill-submissions/{submission_id}/review-draft")
def save_skill_submission_review_draft(
    submission_id: str,
    payload: SkillSubmissionReviewDraftIn,
    _: str = Depends(require_submission_role(SUBMISSION_REVIEW_ROLES)),
    db: Session = Depends(get_db),
) -> dict:
    data = SkillSubmissionService(db).save_review_draft(submission_id, payload)
    return success(data.model_dump())
