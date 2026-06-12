from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.github_skills.models import SkillGithubSource
from app.modules.skill.models import Skill
from app.modules.skills.service import SkillService


def main() -> None:
    db = SessionLocal()
    try:
        service = SkillService(db)
        rows = db.execute(
            select(Skill, SkillGithubSource)
            .join(SkillGithubSource, SkillGithubSource.skill_id == Skill.id)
            .where(
                Skill.status == "published",
                Skill.deleted_at.is_(None),
            )
            .order_by(SkillGithubSource.repo_full_name.asc(), Skill.published_at.desc(), Skill.created_at.desc())
        ).all()
        skill_ids = [skill.id for skill, _ in rows]
        _, primary_category_map = service._skill_category_maps(skill_ids)

        grouped: dict[str, dict] = defaultdict(lambda: {"repo": "", "githubUrl": "", "stars": 0, "skills": []})

        for skill, source in rows:
            primary_category = primary_category_map.get(skill.id)
            runtime_labels = service._infer_runtimes(
                title=skill.title,
                summary=skill.summary,
                source_name=skill.source_name,
                source_url=skill.source_url,
                original_author=skill.original_author,
                recommended_models=skill.recommended_models or [],
                tags=[],
                skill_type=skill.type,
            )
            subtype = service._infer_subtype(
                title=skill.title,
                summary=skill.summary,
                runtimes=runtime_labels,
                skill_type=skill.type,
            )
            language = service._infer_language(title=skill.title, summary=skill.summary)

            bucket = grouped[source.repo_full_name]
            bucket["repo"] = source.repo_full_name
            bucket["githubUrl"] = source.github_url
            bucket["stars"] = int(source.stars_count or 0)
            bucket["skills"].append(
                {
                    "title": skill.title,
                    "slug": skill.slug,
                    "type": skill.type,
                    "primaryCategory": {
                        "name": primary_category.name if primary_category else None,
                        "slug": primary_category.slug if primary_category else None,
                    },
                    "sourceName": skill.source_name,
                    "runtimeLabels": runtime_labels,
                    "primaryRuntime": runtime_labels[0] if runtime_labels else None,
                    "subtype": subtype,
                    "language": language,
                    "publishedAt": skill.published_at.isoformat() if skill.published_at else None,
                }
            )

        report = {
            "repoCount": len(grouped),
            "skillCount": sum(len(item["skills"]) for item in grouped.values()),
            "repos": sorted(grouped.values(), key=lambda item: (-item["stars"], item["repo"])),
        }

        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
