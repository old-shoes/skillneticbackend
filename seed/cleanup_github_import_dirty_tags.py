from __future__ import annotations

import argparse

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.github_skills.models import GithubSkillImport


DIRTY = {"投资研究", "供应链", "产业链", "股票研究", "市场扫描"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean stale dirty tags from github_skill_imports.parsed_tags")
    parser.add_argument("--repo", help="Only process one repo_full_name, e.g. FoundationAgents/MetaGPT")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    touched = 0
    try:
        stmt = select(GithubSkillImport).order_by(GithubSkillImport.created_at.asc())
        if args.repo:
            stmt = stmt.where(GithubSkillImport.repo_full_name == args.repo)
        rows = db.scalars(stmt).all()
        for row in rows:
            tags = list(row.parsed_tags or [])
            cleaned = [tag for tag in tags if tag not in DIRTY]
            if cleaned == tags:
                continue
            row.parsed_tags = cleaned
            touched += 1
            print(f"cleaned import={row.id} repo={row.repo_full_name} tags={cleaned}")
        if args.dry_run:
            db.rollback()
            print({"touched": touched, "dry_run": True})
            return
        db.commit()
        print({"touched": touched})
    finally:
        db.close()


if __name__ == "__main__":
    main()
