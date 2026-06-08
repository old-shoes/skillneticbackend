from __future__ import annotations

import argparse
from typing import Iterable, Optional

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.github_skills.models import GithubSkillImport
from app.modules.github_skills.service import GithubSkillService
from app.modules.skill.models import Skill
from app.modules.skill_submissions.models import SkillSubmission
from app.modules.skill_submissions.service import SkillSubmissionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill GitHub submission tags and scenes from repo parsing.")
    parser.add_argument("--repo", help="Only process one repo_full_name, e.g. FoundationAgents/MetaGPT")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of submissions to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    return parser.parse_args()


def _iter_github_submissions(
    db,
    *,
    repo_full_name: Optional[str] = None,
    limit: int = 0,
) -> Iterable[SkillSubmission]:
    stmt = (
        select(SkillSubmission)
        .where(
            SkillSubmission.deleted_at.is_(None),
            SkillSubmission.github_url.is_not(None),
        )
        .order_by(SkillSubmission.created_at.asc())
    )
    if repo_full_name:
        stmt = stmt.where(SkillSubmission.repo_full_name == repo_full_name)
    if limit > 0:
        stmt = stmt.limit(limit)
    return db.scalars(stmt).all()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    github_service = GithubSkillService(db)
    submission_service = SkillSubmissionService(db)
    touched = 0
    updated_skills = 0
    failed = 0

    try:
        submissions = _iter_github_submissions(db, repo_full_name=args.repo, limit=args.limit)
        for submission in submissions:
            github_url = (submission.github_url or "").strip()
            if not github_url:
                continue
            try:
                parsed = github_service.parse_repo(github_url)
            except Exception as exc:
                import_row = db.scalar(
                    select(GithubSkillImport)
                    .where(GithubSkillImport.github_url == github_url)
                    .order_by(GithubSkillImport.created_at.desc())
                )
                if import_row is None:
                    failed += 1
                    print(f"failed submission={submission.id} repo={submission.repo_full_name or github_url} error={exc}")
                    continue

                fallback_text = "\n".join(
                    filter(
                        None,
                        [
                            submission.title,
                            submission.summary,
                            submission.description,
                            import_row.parsed_description,
                            import_row.raw_readme_preview,
                            import_row.raw_skill_md_preview,
                        ],
                    )
                )
                fallback_tags = github_service._infer_tags(fallback_text)
                fallback_use_cases = github_service._infer_use_cases(fallback_text)
                parsed = type(
                    "FallbackParsed",
                    (),
                    {
                        "parsed": type(
                            "ParsedPayload",
                            (),
                            {
                                "tags": fallback_tags,
                                "use_cases": fallback_use_cases,
                                "category": import_row.parsed_category,
                                "skill_type": import_row.parsed_skill_type,
                                "difficulty": import_row.parsed_difficulty,
                            },
                        )(),
                    },
                )()
                print(
                    f"fallback submission={submission.id} repo={submission.repo_full_name or github_url} "
                    f"reason={exc} tags={fallback_tags} use_cases={fallback_use_cases}"
                )

            before_tags = list(submission.tags or [])
            before_use_cases = list(submission.use_cases or [])
            next_tags = list(parsed.parsed.tags or [])
            next_use_cases = list(parsed.parsed.use_cases or [])

            changed = before_tags != next_tags or before_use_cases != next_use_cases
            submission.tags = next_tags
            submission.use_cases = next_use_cases

            if parsed.parsed.category:
                category = github_service._find_category(parsed.parsed.category)
                if category is not None:
                    submission.category_id = category.id
                    submission.category_name = category.name

            if parsed.parsed.skill_type:
                submission.skill_type = parsed.parsed.skill_type
            if parsed.parsed.difficulty:
                submission.difficulty = parsed.parsed.difficulty

            if submission.approved_skill_id:
                skill = db.get(Skill, submission.approved_skill_id)
                if skill is not None and skill.deleted_at is None:
                    skill.use_case = next_use_cases[0] if next_use_cases else None
                    skill.search_keywords = " ".join([submission.title, submission.summary, *next_tags])
                    submission_service._sync_submission_skill_tags(submission, skill)
                    updated_skills += 1
                    changed = True

            if changed:
                touched += 1
                print(
                    "updated",
                    f"submission={submission.id}",
                    f"repo={submission.repo_full_name or github_url}",
                    f"tags={next_tags}",
                    f"use_cases={next_use_cases}",
                )

        if args.dry_run:
            db.rollback()
            print(
                f"dry_run_complete submissions={len(submissions)} touched={touched} skills={updated_skills} failed={failed}"
            )
            return

        db.commit()
        print(f"backfill_complete submissions={len(submissions)} touched={touched} skills={updated_skills} failed={failed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
