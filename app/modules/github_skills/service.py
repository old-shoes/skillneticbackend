from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, parse, request
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.category.models import Category
from app.modules.github_skills.models import GithubSkillImport, GithubSkillImportBatch, SkillGithubSource
from app.modules.github_skills.schemas import (
    GithubRepoPreview,
    GithubSkillBatchImportIn,
    GithubSkillBatchImportItemOut,
    GithubSkillBatchImportOut,
    GithubSkillImportApproveIn,
    GithubSkillImportApproveOut,
    GithubSkillImportCreateIn,
    GithubSkillImportCreateOut,
    GithubSkillImportListItemOut,
    GithubSkillParseOut,
    GithubSkillParsedOut,
    GithubSkillSyncOut,
)
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag, Tag


GITHUB_HOST_RE = re.compile(r"^(?:https://|git@|ssh://git@)?github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/#?]+?)(?:\.git)?/?$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
README_LIMIT = 8000
SUMMARY_ZH_LIMIT = 120
SUMMARY_EN_LIMIT = 180


@dataclass
class ParsedGithubUrl:
    owner: str
    repo: str
    repo_full_name: str
    normalized_url: str
    clone_url: str


class GithubSkillService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def parse_github_url(self, raw_url: str) -> ParsedGithubUrl:
        value = (raw_url or "").strip()
        if value.startswith("github.com/"):
            value = "https://" + value
        match = GITHUB_HOST_RE.match(value)
        if not match:
            raise HTTPException(status_code=400, detail="invalid github url")
        owner = match.group("owner").strip()
        repo = match.group("repo").strip()
        if not owner or not repo:
            raise HTTPException(status_code=400, detail="invalid github url")
        repo = repo[:-4] if repo.endswith(".git") else repo
        if repo.lower().endswith(".git"):
            repo = repo[:-4]
        normalized_url = f"https://github.com/{owner}/{repo}"
        clone_url = normalized_url + ".git"
        return ParsedGithubUrl(
            owner=owner,
            repo=repo,
            repo_full_name=f"{owner}/{repo}",
            normalized_url=normalized_url,
            clone_url=clone_url,
        )

    def _github_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Skillnetic-GitHub-Importer",
        }
        token = settings.github_api_token.strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _github_json(self, url: str) -> Dict[str, Any]:
        req = request.Request(url, headers=self._github_headers())
        try:
            with request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 404:
                raise HTTPException(status_code=404, detail="GitHub 仓库不存在或不可访问") from exc
            if exc.code == 403 and "rate limit" in detail.lower():
                raise HTTPException(status_code=429, detail="GITHUB_RATE_LIMITED") from exc
            raise HTTPException(status_code=502, detail=f"github api failed: {exc.code}") from exc
        except error.URLError as exc:
            raise HTTPException(status_code=502, detail="failed to connect to github api") from exc

    def _repo_api(self, parsed: ParsedGithubUrl) -> Dict[str, Any]:
        return self._github_json(f"https://api.github.com/repos/{parsed.repo_full_name}")

    def _contents_api(self, parsed: ParsedGithubUrl, path: str) -> Optional[Dict[str, Any]]:
        try:
            return self._github_json(f"https://api.github.com/repos/{parsed.repo_full_name}/contents/{parse.quote(path)}")
        except HTTPException as exc:
            if exc.status_code == 404:
                return None
            raise

    def _decode_content(self, payload: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if not payload:
            return None, None, None
        content = payload.get("content")
        path = payload.get("path")
        sha = payload.get("sha")
        if not content:
            return None, path, sha
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
        return decoded, path, sha

    def _extract_frontmatter(self, content: Optional[str]) -> Tuple[Dict[str, Any], str]:
        if not content:
            return {}, ""
        match = FRONTMATTER_RE.match(content)
        if not match:
            return {}, content
        frontmatter_text = match.group(1)
        body = content[match.end():]
        result: Dict[str, Any] = {}
        stack: List[Tuple[int, Dict[str, Any]]] = [(0, result)]
        for raw_line in frontmatter_text.splitlines():
            line = raw_line.rstrip()
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            key_part, _, value_part = line.strip().partition(":")
            key = key_part.strip()
            value = value_part.strip().strip("\"'")
            while len(stack) > 1 and indent <= stack[-1][0]:
                stack.pop()
            current = stack[-1][1]
            if not value:
                child: Dict[str, Any] = {}
                current[key] = child
                stack.append((indent, child))
            else:
                current[key] = value
        return result, body

    def _first_paragraph(self, text: str) -> str:
        for block in re.split(r"\n\s*\n", text):
            stripped = block.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
        return text.strip()

    def _truncate_summary(self, text: str) -> str:
        stripped = re.sub(r"\s+", " ", text.strip())
        if not stripped:
            return ""
        if re.search(r"[\u4e00-\u9fff]", stripped):
            return stripped[:SUMMARY_ZH_LIMIT]
        return stripped[:SUMMARY_EN_LIMIT]

    def _recommend_meta(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
        haystack = text.lower()
        if any(word in haystack for word in ["investment", "market", "stock", "supply-chain", "value-chain", "research"]):
            return "data-business-analysis", "agent", "advanced", ["投资研究", "供应链", "产业链", "股票研究", "市场扫描"]
        if any(word in haystack for word in ["code", "review", "testing", "architecture", "frontend", "backend"]):
            return "engineering", "workflow", "intermediate", ["代码审查", "测试", "架构", "开发工具"]
        if any(word in haystack for word in ["image", "design", "visual", "poster", "canvas"]):
            return "design-visual", "prompt", "intermediate", ["视觉设计", "图片生成", "创意设计"]
        if any(word in haystack for word in ["writing", "copy", "content", "blog", "article"]):
            return "writing-content", "prompt", "beginner", ["写作", "内容创作", "文案"]
        return None, None, None, []

    def _build_parse_result(self, github_url: str) -> Tuple[GithubSkillParseOut, GithubRepoPreview]:
        parsed_url = self.parse_github_url(github_url)
        repo_json = self._repo_api(parsed_url)
        skill_md_payload = self._contents_api(parsed_url, "SKILL.md")
        readme_payload = self._contents_api(parsed_url, "README.md")
        license_payload = self._contents_api(parsed_url, "LICENSE")

        skill_md_text, skill_md_path, skill_md_sha = self._decode_content(skill_md_payload)
        readme_text, readme_path, readme_sha = self._decode_content(readme_payload)
        _, license_path, license_sha = self._decode_content(license_payload)

        frontmatter, skill_body = self._extract_frontmatter(skill_md_text)
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}

        description = str(frontmatter.get("description") or "").strip()
        repo_description = str(repo_json.get("description") or "").strip()
        readme_first = self._first_paragraph(readme_text or "")
        summary = (
            metadata.get("short-description")
            or metadata.get("short_description")
            or self._truncate_summary(description)
            or self._truncate_summary(readme_first)
            or self._truncate_summary(repo_description)
            or parsed_url.repo
        )
        title = str(frontmatter.get("name") or repo_json.get("name") or parsed_url.repo).strip()
        merged_text = "\n".join(filter(None, [title, description, repo_description, readme_first, skill_body]))
        category, skill_type, difficulty, tags = self._recommend_meta(merged_text)

        parsed = GithubSkillParsedOut(
            title=title,
            summary=summary,
            description=description or repo_description or readme_first or parsed_url.repo,
            category=category,
            skill_type=skill_type,
            difficulty=difficulty,
            tags=tags,
        )
        license_name = None
        if isinstance(repo_json.get("license"), dict):
            license_name = repo_json["license"].get("spdx_id") or repo_json["license"].get("name")
        if not license_name:
            license_name = str(frontmatter.get("license") or "").strip() or None

        output = GithubSkillParseOut(
            repo_full_name=parsed_url.repo_full_name,
            github_url=parsed_url.normalized_url,
            clone_url=parsed_url.clone_url,
            default_branch=repo_json.get("default_branch"),
            repo_description=repo_description or None,
            stars_count=int(repo_json.get("stargazers_count") or 0),
            forks_count=int(repo_json.get("forks_count") or 0),
            watchers_count=int(repo_json.get("subscribers_count") or repo_json.get("watchers_count") or 0),
            open_issues_count=int(repo_json.get("open_issues_count") or 0),
            license=license_name,
            skill_md_found=bool(skill_md_payload),
            readme_found=bool(readme_payload),
            parsed=parsed,
            warnings=[],
        )
        preview = GithubRepoPreview(
            repo=repo_json,
            skill_md_frontmatter=frontmatter,
            skill_md_preview=(skill_md_text or "")[:README_LIMIT] or None,
            readme_preview=(readme_text or "")[:README_LIMIT] or None,
        )
        preview.repo["__skill_md_path"] = skill_md_path
        preview.repo["__skill_md_sha"] = skill_md_sha
        preview.repo["__readme_path"] = readme_path
        preview.repo["__readme_sha"] = readme_sha
        preview.repo["__license_path"] = license_path
        preview.repo["__license_sha"] = license_sha
        return output, preview

    def parse_repo(self, github_url: str) -> GithubSkillParseOut:
        output, _ = self._build_parse_result(github_url)
        return output

    def create_import_draft(self, payload: GithubSkillImportCreateIn, admin: dict) -> GithubSkillImportCreateOut:
        parsed, preview = self._build_parse_result(payload.github_url)
        duplicate_skill_id = self.db.scalar(select(Skill.id).where(Skill.source_name == parsed.repo_full_name, Skill.deleted_at.is_(None)))
        item = GithubSkillImport(
            repo_full_name=parsed.repo_full_name,
            github_url=parsed.github_url,
            import_status="pending_review",
            parsed_title=payload.title,
            parsed_summary=payload.summary,
            parsed_description=parsed.parsed.description,
            parsed_category=payload.category,
            parsed_skill_type=payload.skill_type,
            parsed_difficulty=payload.difficulty,
            parsed_tags=payload.tags,
            parsed_license=parsed.license,
            parsed_original_author=preview.skill_md_frontmatter.get("metadata", {}).get("author") if isinstance(preview.skill_md_frontmatter.get("metadata"), dict) else None,
            raw_repo_json=preview.repo,
            raw_skill_md_frontmatter=preview.skill_md_frontmatter,
            raw_skill_md_preview=preview.skill_md_preview,
            raw_readme_preview=preview.readme_preview,
            duplicate_skill_id=duplicate_skill_id,
            created_by=self._admin_uuid(admin),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return GithubSkillImportCreateOut(import_id=str(item.id), import_status=item.import_status)

    def list_imports(self, status: Optional[str], page: int, page_size: int) -> Tuple[List[GithubSkillImportListItemOut], int]:
        stmt = select(GithubSkillImport).order_by(GithubSkillImport.created_at.desc())
        count_stmt = select(func.count(GithubSkillImport.id))
        if status:
            stmt = stmt.where(GithubSkillImport.import_status == status)
            count_stmt = count_stmt.where(GithubSkillImport.import_status == status)
        total = int(self.db.scalar(count_stmt) or 0)
        rows = self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        return [
            GithubSkillImportListItemOut(
                id=str(item.id),
                repo_full_name=item.repo_full_name,
                github_url=item.github_url,
                import_status=item.import_status,
                parsed_title=item.parsed_title,
                parsed_summary=item.parsed_summary,
                parsed_category=item.parsed_category,
                parsed_skill_type=item.parsed_skill_type,
                parsed_difficulty=item.parsed_difficulty,
                parsed_tags=item.parsed_tags or [],
                parsed_license=item.parsed_license,
                parsed_original_author=item.parsed_original_author,
                duplicate_skill_id=str(item.duplicate_skill_id) if item.duplicate_skill_id else None,
                error_message=item.error_message,
                created_at=item.created_at.isoformat() if item.created_at else None,
                updated_at=item.updated_at.isoformat() if item.updated_at else None,
                batch_id=str(item.batch_id) if item.batch_id else None,
            )
            for item in rows
        ], total

    def approve_import(self, import_id: str, payload: GithubSkillImportApproveIn, admin: dict) -> GithubSkillImportApproveOut:
        item = self._get_import(import_id)
        parsed_repo = item.raw_repo_json or {}
        frontmatter = item.raw_skill_md_frontmatter or {}
        skill = Skill(
            title=item.parsed_title or parsed_repo.get("name") or item.repo_full_name.split("/")[-1],
            slug=self._build_unique_slug(item.parsed_title or item.repo_full_name.split("/")[-1]),
            summary=item.parsed_summary or item.parsed_description or item.repo_full_name,
            content=None,
            cover_icon="agent" if item.parsed_skill_type == "agent" else "prompt",
            difficulty=item.parsed_difficulty or "intermediate",
            type=item.parsed_skill_type or "agent",
            use_case=item.parsed_category,
            search_keywords=",".join(item.parsed_tags or []),
            recommended_models=[],
            is_featured=payload.is_featured,
            status="published" if payload.publish else "draft",
            published_at=datetime.now(timezone.utc) if payload.publish else None,
            source_type="github",
            source_url=item.github_url,
            source_name=item.repo_full_name,
            original_author=item.parsed_original_author or self._raw_author(frontmatter),
            license=item.parsed_license,
            is_verified_source=True,
            last_source_synced_at=datetime.now(timezone.utc),
        )
        category = self._find_category(item.parsed_category)
        if category is not None:
            skill.category_id = category.id
        self.db.add(skill)
        self.db.flush()
        if category is not None:
            self.db.add(SkillCategoryRelation(skill_id=skill.id, category_id=category.id, is_primary=True))
        self._ensure_tags(skill.id, item.parsed_tags or [])
        source = self.db.scalar(select(SkillGithubSource).where(SkillGithubSource.repo_full_name == item.repo_full_name))
        if source is None:
            source = SkillGithubSource(
                skill_id=skill.id,
                repo_full_name=item.repo_full_name,
                owner_login=item.repo_full_name.split("/")[0],
                repo_name=item.repo_full_name.split("/")[-1],
                github_url=item.github_url,
            )
            self.db.add(source)
        repo_json = parsed_repo or {}
        source.skill_id = skill.id
        source.clone_url = repo_json.get("clone_url")
        source.default_branch = repo_json.get("default_branch")
        source.repo_description = repo_json.get("description")
        source.homepage_url = repo_json.get("homepage")
        source.license_key = (repo_json.get("license") or {}).get("key") if isinstance(repo_json.get("license"), dict) else None
        source.license_name = item.parsed_license
        source.original_author = skill.original_author
        source.source_version = self._raw_version(frontmatter)
        source.stars_count = int(repo_json.get("stargazers_count") or 0)
        source.forks_count = int(repo_json.get("forks_count") or 0)
        source.watchers_count = int(repo_json.get("subscribers_count") or repo_json.get("watchers_count") or 0)
        source.open_issues_count = int(repo_json.get("open_issues_count") or 0)
        source.is_archived = bool(repo_json.get("archived"))
        source.is_private = bool(repo_json.get("private"))
        source.skill_md_path = repo_json.get("__skill_md_path")
        source.skill_md_sha = repo_json.get("__skill_md_sha")
        source.readme_path = repo_json.get("__readme_path")
        source.readme_sha = repo_json.get("__readme_sha")
        source.license_path = repo_json.get("__license_path")
        source.license_sha = repo_json.get("__license_sha")
        source.last_commit_sha = repo_json.get("pushed_at")
        source.github_created_at = self._parse_dt(repo_json.get("created_at"))
        source.github_updated_at = self._parse_dt(repo_json.get("updated_at"))
        source.github_pushed_at = self._parse_dt(repo_json.get("pushed_at"))
        source.last_synced_at = datetime.now(timezone.utc)

        item.import_status = "imported" if payload.publish else "approved"
        item.reviewed_by = self._admin_uuid(admin)
        item.reviewed_at = datetime.now(timezone.utc)
        item.duplicate_skill_id = skill.id
        self.db.commit()
        return GithubSkillImportApproveOut(skill_id=str(skill.id), status=skill.status)

    def reject_import(self, import_id: str, reason: str, admin: dict) -> None:
        item = self._get_import(import_id)
        item.import_status = "rejected"
        item.error_message = reason
        item.reviewed_by = self._admin_uuid(admin)
        item.reviewed_at = datetime.now(timezone.utc)
        self.db.commit()

    def sync_skill(self, skill_id: str) -> GithubSkillSyncOut:
        skill = self.db.get(Skill, self._uuid(skill_id, "skill_id"))
        if skill is None or skill.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Skill 不存在")
        if skill.source_type != "github" or not skill.source_name:
            raise HTTPException(status_code=400, detail="not a github skill")
        parsed_url = self.parse_github_url(skill.source_url or f"https://github.com/{skill.source_name}")
        repo_json = self._repo_api(parsed_url)
        source = self.db.scalar(select(SkillGithubSource).where(SkillGithubSource.skill_id == skill.id))
        if source is None:
            raise HTTPException(status_code=404, detail="github source not found")
        source.stars_count = int(repo_json.get("stargazers_count") or 0)
        source.forks_count = int(repo_json.get("forks_count") or 0)
        source.watchers_count = int(repo_json.get("subscribers_count") or repo_json.get("watchers_count") or 0)
        source.open_issues_count = int(repo_json.get("open_issues_count") or 0)
        source.github_updated_at = self._parse_dt(repo_json.get("updated_at"))
        source.github_pushed_at = self._parse_dt(repo_json.get("pushed_at"))
        source.last_synced_at = datetime.now(timezone.utc)
        skill.last_source_synced_at = source.last_synced_at
        self.db.commit()
        return GithubSkillSyncOut(
            last_synced_at=source.last_synced_at.isoformat() if source.last_synced_at else datetime.now(timezone.utc).isoformat(),
            stars_count=source.stars_count,
            forks_count=source.forks_count,
            github_updated_at=source.github_updated_at.isoformat() if source.github_updated_at else None,
        )

    def batch_import(self, payload: GithubSkillBatchImportIn, admin: dict) -> GithubSkillBatchImportOut:
        if len(payload.items) > 50:
            raise HTTPException(status_code=400, detail="单次最多 50 个 URL")
        batch = GithubSkillImportBatch(
            mode=payload.mode,
            submit_review=payload.submit_review or payload.mode == "submit_review",
            auto_publish=payload.auto_publish,
            default_category=payload.default_category,
            default_skill_type=payload.default_skill_type,
            default_difficulty=payload.default_difficulty,
            total_count=len(payload.items),
            created_by=self._admin_uuid(admin),
        )
        self.db.add(batch)
        self.db.flush()

        results: List[GithubSkillBatchImportItemOut] = []
        success_count = 0
        failed_count = 0
        duplicate_count = 0

        for row in payload.items:
            try:
                parsed, preview = self._build_parse_result(row.github_url)
                duplicate_skill_id = self.db.scalar(select(Skill.id).where(Skill.source_name == parsed.repo_full_name, Skill.deleted_at.is_(None)))
                duplicate_import = self.db.scalar(
                    select(GithubSkillImport.id).where(
                        GithubSkillImport.repo_full_name == parsed.repo_full_name,
                        GithubSkillImport.import_status.in_(("parsed", "pending_review", "approved", "published")),
                    )
                )
                if duplicate_skill_id or duplicate_import:
                    duplicate_count += 1
                    results.append(
                        GithubSkillBatchImportItemOut(
                            github_url=row.github_url,
                            repo_full_name=parsed.repo_full_name,
                            status="duplicate",
                            skill_id=str(duplicate_skill_id) if duplicate_skill_id else None,
                            import_id=str(duplicate_import) if duplicate_import else None,
                            message="已收录或已存在导入记录",
                        )
                    )
                    continue

                if payload.mode == "parse_only":
                    success_count += 1
                    results.append(
                        GithubSkillBatchImportItemOut(
                            github_url=row.github_url,
                            repo_full_name=parsed.repo_full_name,
                            status="parsed",
                            message="解析成功",
                        )
                    )
                    continue

                item = GithubSkillImport(
                    repo_full_name=parsed.repo_full_name,
                    github_url=parsed.github_url,
                    import_status="pending_review" if (payload.submit_review or payload.mode == "submit_review") else "parsed",
                    parsed_title=parsed.parsed.title,
                    parsed_summary=parsed.parsed.summary,
                    parsed_description=parsed.parsed.description,
                    parsed_category=row.category or parsed.parsed.category or payload.default_category,
                    parsed_skill_type=row.skill_type or parsed.parsed.skill_type or payload.default_skill_type,
                    parsed_difficulty=row.difficulty or parsed.parsed.difficulty or payload.default_difficulty,
                    parsed_tags=row.tags or parsed.parsed.tags,
                    parsed_license=parsed.license,
                    parsed_original_author=preview.skill_md_frontmatter.get("metadata", {}).get("author") if isinstance(preview.skill_md_frontmatter.get("metadata"), dict) else None,
                    raw_repo_json=preview.repo,
                    raw_skill_md_frontmatter=preview.skill_md_frontmatter,
                    raw_skill_md_preview=preview.skill_md_preview,
                    raw_readme_preview=preview.readme_preview,
                    batch_id=batch.id,
                    created_by=self._admin_uuid(admin),
                )
                self.db.add(item)
                self.db.flush()
                if payload.auto_publish:
                    approved = self.approve_import(str(item.id), GithubSkillImportApproveIn(publish=True, is_featured=False), admin)
                    success_count += 1
                    results.append(
                        GithubSkillBatchImportItemOut(
                            github_url=row.github_url,
                            repo_full_name=parsed.repo_full_name,
                            status="published",
                            import_id=str(item.id),
                            skill_id=approved.skill_id,
                            message="已直接发布",
                        )
                    )
                else:
                    success_count += 1
                    results.append(
                        GithubSkillBatchImportItemOut(
                            github_url=row.github_url,
                            repo_full_name=parsed.repo_full_name,
                            status="pending_review" if item.import_status == "pending_review" else "created",
                            import_id=str(item.id),
                            message="已创建导入草稿" if item.import_status == "parsed" else "已进入待审核",
                        )
                    )
            except HTTPException as exc:
                failed_count += 1
                results.append(
                    GithubSkillBatchImportItemOut(
                        github_url=row.github_url,
                        status="failed",
                        error_code="GITHUB_RATE_LIMITED" if exc.detail == "GITHUB_RATE_LIMITED" else "IMPORT_FAILED",
                        message=str(exc.detail),
                    )
                )

        batch.success_count = success_count
        batch.failed_count = failed_count
        batch.duplicate_count = duplicate_count
        self.db.commit()
        return GithubSkillBatchImportOut(
            batch_id=str(batch.id),
            total=len(payload.items),
            success_count=success_count,
            failed_count=failed_count,
            duplicate_count=duplicate_count,
            items=results,
        )

    def get_batch_detail(self, batch_id: str):
        batch = self.db.get(GithubSkillImportBatch, self._uuid(batch_id, "batch_id"))
        if batch is None:
            raise HTTPException(status_code=404, detail="batch not found")
        rows = self.db.scalars(
            select(GithubSkillImport)
            .where(GithubSkillImport.batch_id == batch.id)
            .order_by(GithubSkillImport.created_at.asc())
        ).all()
        items = [
            GithubSkillImportListItemOut(
                id=str(item.id),
                repo_full_name=item.repo_full_name,
                github_url=item.github_url,
                import_status=item.import_status,
                parsed_title=item.parsed_title,
                parsed_summary=item.parsed_summary,
                parsed_category=item.parsed_category,
                parsed_skill_type=item.parsed_skill_type,
                parsed_difficulty=item.parsed_difficulty,
                parsed_tags=item.parsed_tags or [],
                parsed_license=item.parsed_license,
                parsed_original_author=item.parsed_original_author,
                duplicate_skill_id=str(item.duplicate_skill_id) if item.duplicate_skill_id else None,
                error_message=item.error_message,
                created_at=item.created_at.isoformat() if item.created_at else None,
                updated_at=item.updated_at.isoformat() if item.updated_at else None,
                batch_id=str(item.batch_id) if item.batch_id else None,
            )
            for item in rows
        ]
        from app.modules.github_skills.schemas import GithubSkillBatchDetailOut

        return GithubSkillBatchDetailOut(
            batch_id=str(batch.id),
            mode=batch.mode,
            submit_review=batch.submit_review,
            auto_publish=batch.auto_publish,
            default_category=batch.default_category,
            default_skill_type=batch.default_skill_type,
            default_difficulty=batch.default_difficulty,
            total_count=batch.total_count,
            success_count=batch.success_count,
            failed_count=batch.failed_count,
            duplicate_count=batch.duplicate_count,
            created_at=batch.created_at.isoformat() if batch.created_at else None,
            items=items,
        )

    def _get_import(self, import_id: str) -> GithubSkillImport:
        item = self.db.get(GithubSkillImport, self._uuid(import_id, "import_id"))
        if item is None:
            raise HTTPException(status_code=404, detail="import not found")
        return item

    def _build_unique_slug(self, value: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip().lower()).strip("-") or "github-skill"
        slug = base[:140]
        index = 2
        while self.db.scalar(select(Skill.id).where(Skill.slug == slug)) is not None:
            suffix = f"-{index}"
            slug = f"{base[:140-len(suffix)]}{suffix}"
            index += 1
        return slug

    def _find_category(self, slug: Optional[str]) -> Optional[Category]:
        if not slug:
            return None
        return self.db.scalar(
            select(Category).where(
                Category.slug == slug,
                Category.deleted_at.is_(None),
                Category.is_enabled.is_(True),
            )
        )

    def _ensure_tags(self, skill_id: UUID, names: List[str]) -> None:
        for name in names:
            cleaned = (name or "").strip()
            if not cleaned:
                continue
            slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", cleaned.lower()).strip("-") or cleaned
            tag = self.db.scalar(select(Tag).where(Tag.slug == slug))
            if tag is None:
                tag = Tag(name=cleaned, slug=slug, type="type", is_enabled=True)
                self.db.add(tag)
                self.db.flush()
            exists = self.db.scalar(select(SkillTag).where(SkillTag.skill_id == skill_id, SkillTag.tag_id == tag.id))
            if exists is None:
                self.db.add(SkillTag(skill_id=skill_id, tag_id=tag.id))

    def _admin_uuid(self, admin: dict) -> Optional[UUID]:
        raw = (admin or {}).get("id")
        if not raw or raw == "dev-admin":
            return None
        try:
            return UUID(str(raw))
        except ValueError:
            return None

    def _uuid(self, raw: str, field_name: str) -> UUID:
        try:
            return UUID(raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid {field_name}") from exc

    def _parse_dt(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _raw_author(self, frontmatter: Dict[str, Any]) -> Optional[str]:
        metadata = frontmatter.get("metadata")
        if isinstance(metadata, dict):
            return metadata.get("author")
        return None

    def _raw_version(self, frontmatter: Dict[str, Any]) -> Optional[str]:
        metadata = frontmatter.get("metadata")
        if isinstance(metadata, dict):
            return metadata.get("version")
        return None
