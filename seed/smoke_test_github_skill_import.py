from datetime import datetime, timezone
from types import MethodType

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.github_skills.models import GithubSkillImport, SkillGithubSource
from app.modules.github_skills.schemas import (
    GithubRepoPreview,
    GithubSkillBatchImportIn,
    GithubSkillBatchItemIn,
    GithubSkillImportApproveIn,
    GithubSkillImportCreateIn,
    GithubSkillParseOut,
    GithubSkillParsedOut,
)
from app.modules.github_skills.service import GithubSkillService
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag


ADMIN = {"id": "dev-admin", "role": "super_admin"}
TEST_REPO = "codex/smoke-github-skill"
TEST_URL = "https://github.com/codex/smoke-github-skill"


def make_parse(repo_full_name: str, github_url: str, title_suffix: str = ""):
    parsed = GithubSkillParseOut(
        repo_full_name=repo_full_name,
        github_url=github_url,
        clone_url=github_url + ".git",
        default_branch="main",
        repo_description="Smoke test repo",
        stars_count=42,
        forks_count=7,
        watchers_count=5,
        open_issues_count=1,
        license="MIT",
        skill_md_found=True,
        readme_found=True,
        parsed=GithubSkillParsedOut(
            title="Smoke Test Skill" + title_suffix,
            summary="Smoke summary" + title_suffix,
            description="Smoke description" + title_suffix,
            category="engineering",
            skill_type="workflow",
            difficulty="intermediate",
            tags=["测试", "自动化"],
        ),
        warnings=[],
    )
    preview = GithubRepoPreview(
        repo={
            "name": "smoke-github-skill",
            "clone_url": github_url + ".git",
            "default_branch": "main",
            "description": "Smoke test repo",
            "homepage": "https://example.com",
            "license": {"key": "mit", "name": "MIT"},
            "stargazers_count": 42,
            "forks_count": 7,
            "subscribers_count": 5,
            "watchers_count": 5,
            "open_issues_count": 1,
            "archived": False,
            "private": False,
            "created_at": "2026-06-01T00:00:00Z",
            "updated_at": "2026-06-05T00:00:00Z",
            "pushed_at": "2026-06-06T00:00:00Z",
            "__skill_md_path": "SKILL.md",
            "__skill_md_sha": "skillsha",
            "__readme_path": "README.md",
            "__readme_sha": "readmesha",
            "__license_path": "LICENSE",
            "__license_sha": "licensesha",
        },
        skill_md_frontmatter={"metadata": {"author": "codex", "version": "1.0.0"}},
        skill_md_preview="---\nname: Smoke Test Skill\n---",
        readme_preview="# Smoke Test Skill",
    )
    return parsed, preview


def cleanup(db):
    skill_ids = list(
        db.scalars(
            select(Skill.id).where(
                Skill.source_name.in_([TEST_REPO, "codex/batch-skill-1", "codex/batch-skill-2", "codex/batch-skill-3"])
            )
        ).all()
    )
    if skill_ids:
        db.execute(delete(SkillCategoryRelation).where(SkillCategoryRelation.skill_id.in_(skill_ids)))
        db.execute(delete(SkillTag).where(SkillTag.skill_id.in_(skill_ids)))
        db.execute(delete(SkillGithubSource).where(SkillGithubSource.skill_id.in_(skill_ids)))
        db.execute(delete(GithubSkillImport).where(GithubSkillImport.duplicate_skill_id.in_(skill_ids)))
        db.execute(delete(Skill).where(Skill.id.in_(skill_ids)))
    db.execute(
        delete(SkillGithubSource).where(
            SkillGithubSource.repo_full_name.in_([TEST_REPO, "codex/batch-skill-1", "codex/batch-skill-2", "codex/batch-skill-3"])
        )
    )
    db.execute(
        delete(GithubSkillImport).where(
            GithubSkillImport.repo_full_name.in_([TEST_REPO, "codex/batch-skill-1", "codex/batch-skill-2", "codex/batch-skill-3"])
        )
    )
    db.commit()


def main():
    db = SessionLocal()
    try:
        cleanup(db)
        service = GithubSkillService(db)

        def fake_build(self, github_url: str):
            if github_url.endswith("batch-skill-1.git") or github_url.endswith("batch-skill-1"):
                return make_parse("codex/batch-skill-1", "https://github.com/codex/batch-skill-1")
            if github_url.endswith("batch-skill-2.git") or github_url.endswith("batch-skill-2"):
                return make_parse("codex/batch-skill-2", "https://github.com/codex/batch-skill-2", " 2")
            if github_url.endswith("batch-skill-3.git") or github_url.endswith("batch-skill-3"):
                return make_parse("codex/batch-skill-3", "https://github.com/codex/batch-skill-3", " 3")
            return make_parse(TEST_REPO, TEST_URL)

        def fake_repo_api(self, parsed):
            return {
                "stargazers_count": 88,
                "forks_count": 12,
                "subscribers_count": 9,
                "watchers_count": 9,
                "open_issues_count": 3,
                "updated_at": "2026-06-06T08:00:00Z",
                "pushed_at": "2026-06-06T09:00:00Z",
            }

        service._build_parse_result = MethodType(fake_build, service)
        service._repo_api = MethodType(fake_repo_api, service)

        create_out = service.create_import_draft(
            GithubSkillImportCreateIn(
                github_url=TEST_URL,
                title="Smoke Test Skill",
                summary="Smoke summary",
                category="engineering",
                skill_type="workflow",
                difficulty="intermediate",
                tags=["测试", "自动化"],
            ),
            ADMIN,
        )
        imports, total = service.list_imports("pending_review", 1, 20)
        approve_out = service.approve_import(create_out.import_id, GithubSkillImportApproveIn(publish=True), ADMIN)
        skill = db.get(Skill, service._uuid(approve_out.skill_id, "skill_id"))
        source = db.scalar(select(SkillGithubSource).where(SkillGithubSource.skill_id == skill.id))
        sync_out = service.sync_skill(str(skill.id))
        batch_out = service.batch_import(
            GithubSkillBatchImportIn(
                mode="create_import",
                submit_review=True,
                auto_publish=False,
                default_category="engineering",
                default_skill_type="workflow",
                default_difficulty="intermediate",
                items=[
                    GithubSkillBatchItemIn(github_url="https://github.com/codex/batch-skill-1.git"),
                    GithubSkillBatchItemIn(github_url="https://github.com/codex/batch-skill-2.git"),
                    GithubSkillBatchItemIn(github_url="https://github.com/codex/batch-skill-1.git"),
                ],
            ),
            ADMIN,
        )
        batch_detail = service.get_batch_detail(batch_out.batch_id)

        print(
            {
                "create_import_id": create_out.import_id,
                "pending_review_total": total,
                "pending_review_count_page": len(imports),
                "approved_skill_id": approve_out.skill_id,
                "approved_skill_status": approve_out.status,
                "source_repo": source.repo_full_name if source else None,
                "source_stars_after_sync": sync_out.stars_count,
                "batch_id": batch_out.batch_id,
                "batch_success_count": batch_out.success_count,
                "batch_duplicate_count": batch_out.duplicate_count,
                "batch_items": [item.status for item in batch_out.items],
                "batch_detail_items": len(batch_detail.items),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
