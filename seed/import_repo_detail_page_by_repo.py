from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.category.models import Category  # noqa: F401
from app.modules.skill.models import Skill


ROOT_DIR = Path(__file__).resolve().parents[3]
SOURCE_FILE = ROOT_DIR / "repo_detail_page_by_repo.md"

SECTION_HEADER_RE = re.compile(r"(?m)^##\s+\d+\.\s+(.+?)\s*$")
FIELD_RE = re.compile(r"\*\*(.+?)\*\*：")


def load_source_text() -> str:
    return SOURCE_FILE.read_text(encoding="utf-8")


def parse_sections(text: str) -> list[dict[str, object]]:
    matches = list(SECTION_HEADER_RE.finditer(text))
    sections: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        repo_full_name = match.group(1).strip()
        section_start = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[section_start:section_end].strip()
        fields = parse_fields(body)
        sections.append(
            {
                "repo_full_name": repo_full_name,
                "body": body,
                "fields": fields,
            }
        )
    return sections


def parse_fields(body: str) -> dict[str, str]:
    matches = list(FIELD_RE.finditer(body))
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        label = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        fields[label] = content
    return fields


def build_detail_markdown(repo_full_name: str, fields: dict[str, str]) -> str:
    parts: list[str] = []

    github_url = fields.get("GitHub", "").strip()
    if github_url:
        github_url = github_url.strip("`")
        parts.append("## 项目链接")
        parts.append(f"- 仓库：[{repo_full_name}]({github_url})")

    main_labels = [
        "项目定位",
        "它解决什么问题",
        "详细介绍",
        "怎么用 / 怎么接入",
        "适合谁",
        "核心卖点",
        "局限与注意点",
    ]
    for label in main_labels:
        content = fields.get(label, "").strip()
        if not content:
            continue
        parts.append(f"## {label}")
        parts.append(content)

    tag_lines: list[str] = []
    for label in ["领域分类标签", "使用场景标签", "适用工具标签"]:
        content = fields.get(label, "").strip()
        if content:
            tag_lines.append(f"- {label}：{content}")
    if tag_lines:
        parts.append("## 标签信息")
        parts.extend(tag_lines)

    note = fields.get("备注", "").strip()
    if note:
        parts.append("## 备注")
        parts.append(note)

    return "\n\n".join(parts).strip()


def main() -> None:
    text = load_source_text()
    sections = parse_sections(text)

    db = SessionLocal()
    updated = 0
    missing: list[str] = []

    try:
        for item in sections:
            repo_full_name = str(item["repo_full_name"]).strip()
            fields = item["fields"] if isinstance(item["fields"], dict) else {}
            github_url = str(fields.get("GitHub", "")).strip().strip("`")

            skill = db.scalar(
                select(Skill).where(
                    Skill.deleted_at.is_(None),
                    (Skill.source_name == repo_full_name) | (Skill.source_url == github_url),
                )
            )
            if skill is None:
                missing.append(repo_full_name)
                continue

            detail_markdown = build_detail_markdown(repo_full_name, fields)
            if detail_markdown:
                skill.content = detail_markdown
                updated += 1

        db.commit()
        print(
            json.dumps(
                {
                    "source_file": str(SOURCE_FILE),
                    "section_count": len(sections),
                    "updated": updated,
                    "missing": missing,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
