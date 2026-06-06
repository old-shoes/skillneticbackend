from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import success
from app.modules.admin_common.deps import get_current_admin
from app.modules.admin_common.permissions import require_permission
from app.modules.admin_common.response import page_response
from app.modules.github_skills.schemas import (
    GithubSkillBatchImportIn,
    GithubSkillImportApproveIn,
    GithubSkillImportCreateIn,
    GithubSkillImportRejectIn,
    GithubSkillParseIn,
)
from app.modules.github_skills.service import GithubSkillService


router = APIRouter()


@router.post("/parse")
def parse_github_repo(
    payload: GithubSkillParseIn,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill:read")
    data = GithubSkillService(db).parse_repo(payload.github_url)
    return success(data.model_dump())


@router.post("/imports")
def create_import(
    payload: GithubSkillImportCreateIn,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill_submission:review")
    data = GithubSkillService(db).create_import_draft(payload, admin)
    return success(data.model_dump())


@router.get("/imports")
def list_imports(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill:read")
    items, total = GithubSkillService(db).list_imports(status, page, pageSize)
    return page_response([item.model_dump() for item in items], page, pageSize, total)


@router.post("/imports/{import_id}/approve")
def approve_import(
    import_id: str,
    payload: GithubSkillImportApproveIn,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill_submission:review")
    data = GithubSkillService(db).approve_import(import_id, payload, admin)
    return success(data.model_dump())


@router.post("/imports/{import_id}/reject")
def reject_import(
    import_id: str,
    payload: GithubSkillImportRejectIn,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill_submission:review")
    GithubSkillService(db).reject_import(import_id, payload.reason, admin)
    return success()


@router.post("/{skill_id}/sync")
def sync_github_skill(
    skill_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill:read")
    data = GithubSkillService(db).sync_skill(skill_id)
    return success(data.model_dump())


@router.post("/batch-import")
def batch_import(
    payload: GithubSkillBatchImportIn,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill_submission:review")
    data = GithubSkillService(db).batch_import(payload, admin)
    return success(data.model_dump())


@router.get("/batches/{batch_id}")
def get_batch_detail(
    batch_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    require_permission(admin, "skill:read")
    data = GithubSkillService(db).get_batch_detail(batch_id)
    return success(data.model_dump())
