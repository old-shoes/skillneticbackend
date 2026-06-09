from __future__ import annotations

import base64
import json
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib import error, parse, request
from uuid import UUID

import certifi
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
    GithubTaxonomySuggestionOut,
)
from app.modules.skill.models import Skill, SkillCategoryRelation, SkillTag, Tag


GITHUB_HOST_RE = re.compile(r"^(?:https://|git@|ssh://git@)?github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/#?]+?)(?:\.git)?/?$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
README_LIMIT = 8000
SUMMARY_ZH_LIMIT = 120
SUMMARY_EN_LIMIT = 180
USE_CASE_KEYWORDS = {
    "content_creation": [
        "content creation",
        "copywriting",
        "writing",
        "article",
        "blog",
        "newsletter",
        "storytelling",
        "内容创作",
        "写作",
        "文案",
        "文章",
    ],
    "social_media": [
        "social media",
        "xiaohongshu",
        "tiktok",
        "instagram",
        "linkedin",
        "社交媒体",
        "小红书",
        "抖音",
        "运营",
    ],
    "marketing": [
        "marketing",
        "growth",
        "seo",
        "campaign",
        "conversion",
        "lead generation",
        "推广",
        "营销",
        "投放",
        "转化",
    ],
    "ecommerce": [
        "ecommerce",
        "shopify",
        "amazon",
        "product listing",
        "sku",
        "电商",
        "商品",
        "店铺",
    ],
    "productivity": [
        "productivity",
        "workflow",
        "automation",
        "knowledge base",
        "notion",
        "office",
        "clipboard",
        "pasteboard",
        "copy and paste",
        "copy paste",
        "clipboard manager",
        "menu bar",
        "hotkey",
        "shortcut",
        "floating panel",
        "always-on-top",
        "always on top",
        "screenshot",
        "screen capture",
        "desktop utility",
        "utility app",
        "mac utility",
        "macos utility",
        "macos app",
        "swiftui app",
        "效率",
        "自动化",
        "办公",
        "流程",
        "粘贴板",
        "剪贴板",
        "截图",
        "快捷键",
        "菜单栏",
        "置顶窗口",
        "效率工具",
        "桌面工具",
        "macos 应用",
    ],
    "learning": [
        "learning",
        "education",
        "teaching",
        "tutor",
        "study",
        "course",
        "学习",
        "教育",
        "教学",
        "辅导",
    ],
    "data_analysis": [
        "data analysis",
        "analytics",
        "insight",
        "dashboard",
        "sql",
        "excel",
        "spreadsheet",
        "数据分析",
        "研究",
        "报表",
        "洞察",
    ],
    "development": [
        "development",
        "developer",
        "engineering",
        "frontend",
        "backend",
        "coding",
        "programming",
        "testing",
        "debug",
        "api",
        "开发",
        "编程",
        "代码",
        "调试",
        "测试",
    ],
}
USE_CASE_ALIASES = {
    "content": "content_creation",
    "content_creation": "content_creation",
    "social": "social_media",
    "social_media": "social_media",
    "marketing": "marketing",
    "ecommerce": "ecommerce",
    "productivity": "productivity",
    "learning": "learning",
    "education": "learning",
    "data_analysis": "data_analysis",
    "analysis": "data_analysis",
    "development": "development",
    "engineering": "development",
    "software_development": "development",
    "software development": "development",
    "coding": "development",
    "multi_agent_collaboration": "development",
    "multi agent collaboration": "development",
    "code_generation": "development",
    "code generation": "development",
}
USE_CASE_LABELS = {
    "content_creation": "内容创作",
    "social_media": "社交媒体运营",
    "marketing": "营销推广",
    "ecommerce": "电商转化",
    "productivity": "办公提效",
    "learning": "学习辅导",
    "data_analysis": "数据分析",
    "development": "编程开发",
}
USE_CASE_FRONTMATTER_KEYS = (
    "use_cases",
    "use_case",
    "scenarios",
    "scenario",
    "applicable_scenarios",
    "applicable_scenario",
    "适用场景",
    "使用场景",
    "场景",
)
TAG_FRONTMATTER_KEYS = (
    "tags",
    "tag",
    "keywords",
    "keyword",
    "labels",
    "topics",
    "标签",
    "关键字",
)
TAG_KEYWORDS = {
    "代码审查": ["code review", "review", "lint", "静态检查"],
    "测试自动化": ["test", "testing", "pytest", "unit test", "e2e", "自动化测试"],
    "调试排错": ["debug", "troubleshoot", "trace", "排错", "调试"],
    "工作流编排": ["workflow", "pipeline", "automation", "orchestration", "编排"],
    "智能体": ["agent", "multi-agent", "assistant", "copilot", "智能体"],
    "提示词工程": ["prompt", "system prompt", "prompt template", "提示词"],
    "内容创作": ["content creation", "writing", "copywriting", "blog", "article", "文案", "写作"],
    "视觉设计": ["visual design", "poster design", "graphic design", "ui design", "ux design", "设计稿", "海报设计"],
    "办公提效": [
        "clipboard",
        "pasteboard",
        "clipboard manager",
        "copy and paste",
        "copy paste",
        "screenshot",
        "screen capture",
        "menu bar",
        "hotkey",
        "productivity",
        "efficiency",
        "剪贴板",
        "粘贴板",
        "截图",
        "菜单栏",
        "快捷键",
        "办公提效",
        "效率工具",
    ],
    "数据分析": ["data analysis", "analytics", "dashboard", "sql", "excel", "分析", "报表", "data interpreter"],
    "学习研究": ["study", "learning", "education", "tutorial", "course", "学习", "教程"],
    "营销推广": ["marketing", "seo", "campaign", "growth", "营销", "推广"],
    "电商运营": ["ecommerce", "shopify", "amazon", "listing", "sku", "电商"],
    "投资研究": ["investment", "equity research", "financial model", "投研", "投资研究"],
    "股票研究": ["stock", "stocks", "证券", "股票"],
    "市场扫描": ["market scan", "market monitoring", "行情", "市场扫描"],
    "供应链": ["supply chain", "供应链"],
    "产业链": ["value chain", "产业链"],
}
HIGH_RISK_FINANCE_TAGS = {"投资研究", "股票研究", "市场扫描", "供应链", "产业链"}
AGENTIC_REPO_KEYWORDS = {
    "agent",
    "agents",
    "multi-agent",
    "assistant",
    "copilot",
    "prompt",
    "workflow",
    "skill",
    "skills",
    "claude code",
    "codex",
    "cursor",
    "system prompt",
    "template",
    "automation",
}
FINANCE_STRONG_SIGNAL_KEYWORDS = {
    "equity research",
    "financial model",
    "valuation",
    "alpha",
    "portfolio",
    "hedge fund",
    "earnings",
    "securities",
    "a-share",
    "stock pitch",
    "quant",
    "factor investing",
    "行业研究",
    "证券研究",
    "财务建模",
    "估值",
    "基金",
    "研报",
    "量化",
    "投资组合",
}
FINANCE_WEAK_SIGNAL_KEYWORDS = {
    "investment",
    "stock",
    "stocks",
    "supply chain",
    "value chain",
    "market scan",
    "投研",
    "投资研究",
    "股票",
    "供应链",
    "产业链",
    "市场扫描",
}
NOISY_SECTION_TITLES = {
    "news",
    "tutorial",
    "tutorials",
    "support",
    "citation",
    "contact information",
    "contributor form",
    "quickstart & demo video",
    "quickstart",
}
TAG_NOISY_SECTION_TITLES = NOISY_SECTION_TITLES | {
    "quick install / 快速安装",
    "quick install",
    "installation",
    "install",
    "requirements / 系统要求",
    "requirements",
    "system requirements",
    "build from source / 从源码构建",
    "build from source",
    "usage / 使用",
    "usage",
    "project structure / 项目结构",
    "project structure",
    "changelog / 更新日志",
    "changelog",
    "known issues / 已知问题",
    "known issues",
    "license",
}
MODEL_KEYWORDS: Dict[str, List[str]] = {
    "openai": ["openai", "gpt-4", "gpt-4o", "gpt-4.1", "gpt-3.5", "chatgpt"],
    "claude": ["claude", "anthropic"],
    "gemini": ["gemini", "google ai", "google-generativeai"],
    "ollama": ["ollama"],
    "groq": ["groq"],
    "azure-openai": ["azure openai", "azure-openai", "azure_openai"],
    "deepseek": ["deepseek"],
}
GENERIC_TAG_CODES = {
    "github",
    "prompt",
    "tutorial",
    "workflow",
    "paper",
}
SKILL_TYPE_PATTERNS: List[Tuple[str, str, List[str]]] = [
    ("agent-framework", "agent", ["multi-agent framework", "agent framework", "multi agent", "software company", "agent team"]),
    ("sdk-library", "tool_config", ["sdk", "library", "package", "pip install", "python package"]),
    ("cli-tool", "tool_config", ["cli", "command line", "terminal", "npx", "python -m"]),
    ("desktop-tool", "tool_config", ["macos app", "desktop app", "menu bar app", "clipboard manager", "screenshot tool", "swiftui", "swift app"]),
    ("workflow-template", "workflow", ["workflow", "pipeline", "automation", "orchestration"]),
    ("prompt-template", "prompt", ["prompt template", "system prompt", "prompt engineering"]),
    ("github-repo", "workflow", ["github repository", "open source project", "repository"]),
]
SKILL_TYPE_CODE_TO_RUNTIME: Dict[str, str] = {
    "agent-framework": "agent",
    "github-repo": "workflow",
    "sdk-library": "tool_config",
    "cli-tool": "tool_config",
    "desktop-tool": "tool_config",
    "prompt-template": "prompt",
    "workflow-template": "workflow",
}


@dataclass
class ParsedGithubRepo:
    owner: str
    repo: str
    url: str
    repo_full_name: str
    name: str
    description: str
    stars: int
    forks: int
    watchers: int
    open_issues: int
    language: Optional[str]
    license: Optional[str]
    topics: List[str]
    readme_text: str
    readme_texts: List[str]
    skill_md_text: str
    raw_repo: Dict[str, Any]


@dataclass
class TaxonomyCandidate:
    code: str
    name: str
    aliases: List[str]
    keywords: List[str]
    source_type: str


@dataclass
class TaxonomyMatch:
    code: str
    name: str
    score: float
    reason: str


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
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

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
            with request.urlopen(req, timeout=20, context=self.ssl_context) as resp:
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
            raise HTTPException(status_code=502, detail="GitHub API 当前不可达，请检查网络或稍后重试") from exc

    def _repo_api(self, parsed: ParsedGithubUrl) -> Dict[str, Any]:
        return self._github_json(f"https://api.github.com/repos/{parsed.repo_full_name}")

    def _topics_api(self, parsed: ParsedGithubUrl) -> List[str]:
        try:
            payload = self._github_json(f"https://api.github.com/repos/{parsed.repo_full_name}/topics")
        except HTTPException:
            return []
        names = payload.get("names")
        if isinstance(names, list):
            return [str(item).strip() for item in names if str(item).strip()]
        return []

    def _contents_api(self, parsed: ParsedGithubUrl, path: str) -> Optional[Dict[str, Any]]:
        try:
            return self._github_json(f"https://api.github.com/repos/{parsed.repo_full_name}/contents/{parse.quote(path)}")
        except HTTPException as exc:
            if exc.status_code == 404:
                return None
            raise

    def _root_contents_api(self, parsed: ParsedGithubUrl) -> List[Dict[str, Any]]:
        payload = self._contents_api(parsed, "")
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def _markdown_priority(self, path: str, base_name: str) -> Tuple[int, int, str]:
        normalized = path.strip()
        lowered = normalized.lower()
        base = base_name.lower()
        if base == "readme":
            if lowered == "readme_cn.md":
                return (0, 0, normalized)
            if lowered == "readme.zh-cn.md":
                return (0, 1, normalized)
            if lowered == "readme.md":
                return (1, 0, normalized)
        if lowered == f"{base}.zh-cn.md":
            return (2, 0, normalized)
        if re.match(rf"^{re.escape(base)}\.zh(?:[-_].+)?\.md$", lowered):
            return (2, 1, normalized)
        if lowered == f"{base}.en.md":
            return (3, 0, normalized)
        if re.match(rf"^{re.escape(base)}\.en(?:[-_].+)?\.md$", lowered):
            return (3, 1, normalized)
        if lowered == f"{base}.md":
            return (4, 0, normalized)
        if re.match(rf"^{re.escape(base)}(?:\.[^.]+)?\.md$", lowered):
            return (5, 0, normalized)
        return (9, 9, normalized)

    def _preferred_markdown(self, parsed: ParsedGithubUrl, base_name: str) -> Optional[Dict[str, Any]]:
        root_items = self._root_contents_api(parsed)
        prefix = base_name.lower()
        candidates = [
            item for item in root_items
            if str(item.get("type") or "") == "file"
            and str(item.get("name") or "").lower().startswith(prefix)
            and str(item.get("name") or "").lower().endswith(".md")
        ]
        if not candidates:
            return self._contents_api(parsed, f"{base_name}.md")

        best = sorted(
            candidates,
            key=lambda item: self._markdown_priority(str(item.get("name") or ""), base_name),
        )[0]
        payload = self._contents_api(parsed, str(best.get("path") or best.get("name") or ""))
        if payload:
            return payload
        return self._contents_api(parsed, f"{base_name}.md")

    def _preferred_readme(self, parsed: ParsedGithubUrl) -> Optional[Dict[str, Any]]:
        for candidate in ("README_CN.md", "README.zh-CN.md", "README.md"):
            exact_readme = self._contents_api(parsed, candidate)
            if exact_readme:
                return exact_readme
        return self._preferred_markdown(parsed, "README")

    def _all_readme_payloads(self, parsed: ParsedGithubUrl) -> List[Dict[str, Any]]:
        root_items = self._root_contents_api(parsed)
        candidates = [
            item
            for item in root_items
            if str(item.get("type") or "") == "file"
            and str(item.get("name") or "").lower().startswith("readme")
            and str(item.get("name") or "").lower().endswith(".md")
        ]
        payloads: List[Dict[str, Any]] = []
        seen_paths = set()
        for item in sorted(candidates, key=lambda row: self._markdown_priority(str(row.get("name") or ""), "README")):
            path = str(item.get("path") or item.get("name") or "")
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            payload = self._contents_api(parsed, path)
            if payload:
                payloads.append(payload)
        return payloads

    def _preferred_skill_markdown(self, parsed: ParsedGithubUrl) -> Optional[Dict[str, Any]]:
        return self._preferred_markdown(parsed, "SKILL")

    def _fetch_repo_bundle(self, parsed_url: ParsedGithubUrl) -> Tuple[ParsedGithubRepo, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        repo_json = self._repo_api(parsed_url)
        topics = self._topics_api(parsed_url)
        skill_md_payload = self._preferred_skill_markdown(parsed_url)
        readme_payload = self._preferred_readme(parsed_url)
        all_readme_payloads = self._all_readme_payloads(parsed_url)
        license_payload = self._contents_api(parsed_url, "LICENSE")
        readme_text, _, _ = self._decode_content(readme_payload)
        readme_texts = [text for text, _, _ in (self._decode_content(item) for item in all_readme_payloads) if text]
        skill_md_text, _, _ = self._decode_content(skill_md_payload)

        repo = ParsedGithubRepo(
            owner=parsed_url.owner,
            repo=parsed_url.repo,
            url=parsed_url.normalized_url,
            repo_full_name=parsed_url.repo_full_name,
            name=str(repo_json.get("name") or parsed_url.repo).strip(),
            description=str(repo_json.get("description") or "").strip(),
            stars=int(repo_json.get("stargazers_count") or 0),
            forks=int(repo_json.get("forks_count") or 0),
            watchers=int(repo_json.get("subscribers_count") or repo_json.get("watchers_count") or 0),
            open_issues=int(repo_json.get("open_issues_count") or 0),
            language=str(repo_json.get("language") or "").strip() or None,
            license=(
                (repo_json.get("license") or {}).get("spdx_id")
                if isinstance(repo_json.get("license"), dict)
                else None
            ),
            topics=topics,
            readme_text=readme_text or "",
            readme_texts=readme_texts,
            skill_md_text=skill_md_text or "",
            raw_repo=repo_json,
        )
        return repo, skill_md_payload, readme_payload, license_payload

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
        stack: List[Tuple[int, Any]] = [(0, result)]
        pending_list_key: Optional[str] = None
        lines = frontmatter_text.splitlines()
        for index, raw_line in enumerate(lines):
            line = raw_line.rstrip()
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()
            while len(stack) > 1 and indent < stack[-1][0]:
                stack.pop()
            current = stack[-1][1]

            if stripped.startswith("- "):
                item_value = stripped[2:].strip().strip("\"'")
                if isinstance(current, list):
                    current.append(item_value)
                    continue
                if isinstance(current, dict) and pending_list_key:
                    existing = current.get(pending_list_key)
                    if not isinstance(existing, list):
                        existing = []
                        current[pending_list_key] = existing
                    existing.append(item_value)
                    stack.append((indent + 1, existing))
                    continue

            key_part, _, value_part = stripped.partition(":")
            key = key_part.strip()
            value = value_part.strip().strip("\"'")
            pending_list_key = key

            if not isinstance(current, dict):
                continue

            if not value:
                next_significant = None
                for later_raw in lines[index + 1:]:
                    later = later_raw.rstrip()
                    if not later.strip() or later.strip().startswith("#"):
                        continue
                    next_significant = later
                    break
                next_is_list_item = False
                if next_significant is not None:
                    next_indent = len(next_significant) - len(next_significant.lstrip(" "))
                    next_is_list_item = next_indent > indent and next_significant.strip().startswith("- ")
                if next_is_list_item:
                    child_list: List[str] = []
                    current[key] = child_list
                    stack.append((indent + 1, child_list))
                else:
                    child = {}
                    current[key] = child
                    stack.append((indent + 1, child))
            else:
                current[key] = value
        return result, body

    def _first_paragraph(self, text: str) -> str:
        for block in re.split(r"\n\s*\n", text):
            stripped = block.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
        return text.strip()

    def _strip_noisy_markdown(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text
        cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<img[^>]*>", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
        cleaned = re.sub(r"\[[^\]]+\]\((https?://[^)]+)\)", " ", cleaned)
        cleaned = re.sub(r"https?://\S+", " ", cleaned)

        kept_lines: List[str] = []
        skip_section = False
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                if not skip_section:
                    kept_lines.append("")
                continue

            heading = re.match(r"^#{1,6}\s+(.*)$", line)
            if heading:
                title = heading.group(1).strip().lower()
                skip_section = title in NOISY_SECTION_TITLES
                if not skip_section:
                    kept_lines.append(line)
                continue

            lowered = line.lower()
            if any(token in lowered for token in ["shields.io", "discord", "twitter follow", "producthunt", "youtube", "user-attachments"]):
                continue
            if skip_section:
                continue
            kept_lines.append(line)

        cleaned = "\n".join(kept_lines)
        cleaned = re.sub(r"\buse cases?\b.*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bresearcher\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\breceipt assistant\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bdata interpreter\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[`>*_#\-\[\]\(\)\|]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:6000]

    def _tag_signal_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        kept_lines: List[str] = []
        skip_section = False
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                if not skip_section:
                    kept_lines.append("")
                continue

            heading = re.match(r"^#{1,6}\s+(.*)$", line)
            if heading:
                title = heading.group(1).strip().lower()
                skip_section = title in TAG_NOISY_SECTION_TITLES
                if not skip_section:
                    kept_lines.append(line)
                continue

            if skip_section:
                continue
            kept_lines.append(line)

        return self._strip_noisy_markdown("\n".join(kept_lines))

    def _truncate_summary(self, text: str) -> str:
        stripped = re.sub(r"\s+", " ", text.strip())
        if not stripped:
            return ""
        if re.search(r"[\u4e00-\u9fff]", stripped):
            return stripped[:SUMMARY_ZH_LIMIT]
        return stripped[:SUMMARY_EN_LIMIT]

    def _preferred_description(
        self,
        *,
        frontmatter_description: str,
        skill_body: str,
        readme_text: str,
        repo_description: str,
        selected_skill_path: Optional[str],
        selected_readme_path: Optional[str],
    ) -> str:
        del selected_skill_path
        del selected_readme_path
        if readme_text:
            return readme_text
        if skill_body:
            return skill_body
        if frontmatter_description:
            return frontmatter_description
        if repo_description:
            return repo_description
        return ""

    def _normalize_use_case_value(self, value: str) -> Optional[str]:
        cleaned = re.sub(r"[\s\-]+", "_", (value or "").strip().lower()).strip("_")
        if not cleaned:
            return None
        return USE_CASE_ALIASES.get(cleaned)

    def _normalize_use_case_candidates(self, values: Iterable[str]) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for raw in values:
            mapped = self._normalize_use_case_value(str(raw or ""))
            if not mapped or mapped in seen:
                continue
            seen.add(mapped)
            normalized.append(mapped)
        return normalized

    def _scene_matches_to_use_cases(self, matches: Iterable[TaxonomyMatch]) -> List[str]:
        return self._normalize_use_case_candidates(
            [item.code for item in matches] + [item.name for item in matches]
        )

    def _extract_prompt_role(self, frontmatter: Dict[str, Any], skill_body: str, title: str, skill_type: Optional[str]) -> Optional[str]:
        metadata = frontmatter.get("metadata")
        candidates = [
            frontmatter.get("prompt_role"),
            frontmatter.get("promptRole"),
            frontmatter.get("role"),
            metadata.get("prompt_role") if isinstance(metadata, dict) else None,
            metadata.get("promptRole") if isinstance(metadata, dict) else None,
            metadata.get("role") if isinstance(metadata, dict) else None,
        ]
        for item in candidates:
            value = str(item or "").strip()
            if value:
                return value[:100]

        heading_match = re.search(r"(?im)^#{1,3}\s*(?:role|prompt role|角色|提示词角色)\s*[:：]?\s*(.+?)\s*$", skill_body or "")
        if heading_match:
            return heading_match.group(1).strip()[:100]

        first_line = next((line.strip() for line in (skill_body or "").splitlines() if line.strip()), "")
        if first_line.lower().startswith("you are "):
            return title[:100]

        if skill_type == "agent":
            return (title or "GitHub Agent Skill")[:100]
        if skill_type == "workflow":
            return (title or "GitHub Workflow Skill")[:100]
        return (title or "GitHub Prompt Skill")[:100] if title else None

    def _extract_system_prompt(self, frontmatter: Dict[str, Any], skill_body: str) -> str:
        metadata = frontmatter.get("metadata")
        candidates = [
            frontmatter.get("system_prompt"),
            frontmatter.get("systemPrompt"),
            frontmatter.get("prompt_template"),
            frontmatter.get("promptTemplate"),
            frontmatter.get("template"),
            metadata.get("system_prompt") if isinstance(metadata, dict) else None,
            metadata.get("systemPrompt") if isinstance(metadata, dict) else None,
            metadata.get("prompt_template") if isinstance(metadata, dict) else None,
            metadata.get("promptTemplate") if isinstance(metadata, dict) else None,
        ]
        for item in candidates:
            value = str(item or "").strip()
            if value:
                return value
        return (skill_body or "").strip()

    def _parse_frontmatter_use_cases(self, frontmatter: Dict[str, Any]) -> List[str]:
        raw_values: List[str] = []
        for key in USE_CASE_FRONTMATTER_KEYS:
            value = frontmatter.get(key)
            if value is None:
                metadata = frontmatter.get("metadata")
                if isinstance(metadata, dict):
                    value = metadata.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                raw_values.extend([str(item) for item in value])
            elif isinstance(value, str):
                raw_values.extend([item.strip() for item in re.split(r"[,，/\n|]+", value) if item.strip()])

        normalized: List[str] = []
        seen = set()
        for raw in raw_values:
            mapped = self._normalize_use_case_value(raw)
            if not mapped or mapped in seen:
                continue
            seen.add(mapped)
            normalized.append(mapped)
        return normalized

    def _parse_frontmatter_tags(self, frontmatter: Dict[str, Any]) -> List[str]:
        raw_values: List[str] = []
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
        for key in TAG_FRONTMATTER_KEYS:
            value = frontmatter.get(key)
            if value is None and isinstance(metadata, dict):
                value = metadata.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                raw_values.extend([str(item).strip() for item in value if str(item).strip()])
            elif isinstance(value, str):
                raw_values.extend([item.strip() for item in re.split(r"[,，/\n|]+", value) if item.strip()])

        normalized: List[str] = []
        seen = set()
        for raw in raw_values:
            cleaned = raw.strip()[:50]
            lowered = cleaned.lower()
            if not cleaned or lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", (text or "").lower())).strip()

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        normalized_text = self._normalize_text(text)
        normalized_keyword = self._normalize_text(keyword)
        if not normalized_text or not normalized_keyword:
            return False
        if re.search(r"[\u4e00-\u9fff]", normalized_keyword):
            return normalized_keyword in normalized_text
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])"
        return re.search(pattern, normalized_text) is not None

    def _score_taxonomy_candidate(self, candidate: TaxonomyCandidate, text: str) -> Optional[TaxonomyMatch]:
        normalized = self._normalize_text(text)
        if not normalized:
            return None

        score = 0.0
        reasons: List[str] = []

        code_value = self._normalize_text(candidate.code)
        if code_value and self._contains_keyword(normalized, code_value):
            score += 8
            reasons.append(f"命中 code: {candidate.code}")

        name_value = self._normalize_text(candidate.name)
        if name_value and self._contains_keyword(normalized, name_value):
            score += 6
            reasons.append(f"命中名称: {candidate.name}")

        for alias in candidate.aliases:
            alias_value = self._normalize_text(alias)
            if alias_value and self._contains_keyword(normalized, alias_value):
                score += 5
                reasons.append(f"命中别名: {alias}")

        for keyword in candidate.keywords:
            keyword_value = self._normalize_text(keyword)
            if keyword_value and self._contains_keyword(normalized, keyword_value):
                score += 3 if " " in keyword_value else 1
                reasons.append(f"命中关键词: {keyword}")

        if score <= 0:
            return None

        return TaxonomyMatch(
            code=candidate.code,
            name=candidate.name,
            score=score,
            reason="；".join(reasons),
        )

    def _match_one(self, candidates: Iterable[TaxonomyCandidate], text: str, min_score: float = 3) -> Optional[TaxonomyMatch]:
        matches = [item for item in (self._score_taxonomy_candidate(candidate, text) for candidate in candidates) if item and item.score >= min_score]
        if not matches:
            return None
        matches.sort(key=lambda item: (-item.score, item.code))
        return matches[0]

    def _match_many(
        self,
        candidates: Iterable[TaxonomyCandidate],
        text: str,
        *,
        min_score: float = 2,
        limit: int = 8,
    ) -> List[TaxonomyMatch]:
        matches = [item for item in (self._score_taxonomy_candidate(candidate, text) for candidate in candidates) if item and item.score >= min_score]
        matches.sort(key=lambda item: (-item.score, item.code))
        deduped: List[TaxonomyMatch] = []
        seen = set()
        for item in matches:
            if item.code in seen:
                continue
            seen.add(item.code)
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped

    def _category_candidates(self) -> List[TaxonomyCandidate]:
        rows = self.db.scalars(
            select(Category).where(Category.deleted_at.is_(None), Category.is_enabled.is_(True))
        ).all()
        return [
            TaxonomyCandidate(
                code=item.slug,
                name=item.name,
                aliases=[alias for alias in [item.name_en, item.slug.replace("-", " ")] if alias],
                keywords=[item.description] if item.description else [],
                source_type="category",
            )
            for item in rows
        ]

    def _tag_candidates(self, tag_type: str) -> List[TaxonomyCandidate]:
        rows = self.db.scalars(
            select(Tag).where(
                Tag.deleted_at.is_(None),
                Tag.is_enabled.is_(True),
                Tag.type == tag_type,
            )
        ).all()
        return [
            TaxonomyCandidate(
                code=item.slug,
                name=item.name,
                aliases=[item.slug.replace("-", " ")],
                keywords=[item.name],
                source_type=tag_type,
            )
            for item in rows
        ]

    def _model_candidates(self) -> List[TaxonomyCandidate]:
        return [
            TaxonomyCandidate(code=code, name=code, aliases=[code.replace("-", " ")], keywords=keywords, source_type="model")
            for code, keywords in MODEL_KEYWORDS.items()
        ]

    def _skill_type_candidates(self) -> List[TaxonomyCandidate]:
        return [
            TaxonomyCandidate(
                code=code,
                name=code.replace("-", " "),
                aliases=[label, normalized_type.replace("_", " ")],
                keywords=keywords,
                source_type="skill_type",
            )
            for code, normalized_type, keywords in SKILL_TYPE_PATTERNS
            for label in [code.replace("-", " ")]
        ]

    def _build_search_text(self, repo: ParsedGithubRepo, title: str, description: str, frontmatter: Dict[str, Any], skill_body: str) -> str:
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
        cleaned_description = self._strip_noisy_markdown(description)
        cleaned_readme = self._strip_noisy_markdown(repo.readme_text[:15000])
        cleaned_skill_body = self._strip_noisy_markdown(skill_body[:8000])
        cleaned_skill_md = self._strip_noisy_markdown(repo.skill_md_text[:8000])
        return "\n".join(
            filter(
                None,
                [
                    repo.name,
                    title,
                    repo.description,
                    cleaned_description,
                    repo.language or "",
                    repo.license or "",
                    " ".join(repo.topics or []),
                    json.dumps(frontmatter, ensure_ascii=False) if frontmatter else "",
                    json.dumps(metadata, ensure_ascii=False) if metadata else "",
                    cleaned_readme,
                    cleaned_skill_body,
                    cleaned_skill_md,
                ],
            )
        )

    def _generate_suggested_taxonomies(
        self,
        repo: ParsedGithubRepo,
        matched_tags: List[TaxonomyMatch],
        matched_models: List[TaxonomyMatch],
        category_match: Optional[TaxonomyMatch],
        skill_type_match: Optional[TaxonomyMatch],
    ) -> List[GithubTaxonomySuggestionOut]:
        suggestions: List[GithubTaxonomySuggestionOut] = []
        matched_tag_codes = {item.code for item in matched_tags}
        matched_model_codes = {item.code for item in matched_models}

        if category_match is None:
            suggestions.append(
                GithubTaxonomySuggestionOut(
                    taxonomy_type="category",
                    code="ai-agent-development" if any("agent" in topic.lower() for topic in repo.topics) else "github-repo",
                    name="AI Agent / 智能体开发" if any("agent" in topic.lower() for topic in repo.topics) else "GitHub 仓库",
                    reason="没有匹配到现有分类，建议后台审核确认",
                )
            )

        if skill_type_match is None:
            suggestions.append(
                GithubTaxonomySuggestionOut(
                    taxonomy_type="skill_type",
                    code="agent-framework" if any("agent" in topic.lower() for topic in repo.topics) else "github-repo",
                    name="Agent 框架" if any("agent" in topic.lower() for topic in repo.topics) else "GitHub 仓库",
                    reason="没有匹配到现有类型，建议后台审核确认",
                )
            )

        for topic in repo.topics[:12]:
            code = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
            if not code or code in matched_tag_codes or code in matched_model_codes:
                continue
            suggestions.append(
                GithubTaxonomySuggestionOut(
                    taxonomy_type="tag",
                    code=code[:80],
                    name=topic[:50],
                    reason=f"GitHub topic `{topic}` 未匹配到现有标签",
                )
            )

        deduped: List[GithubTaxonomySuggestionOut] = []
        seen = set()
        for item in suggestions:
            key = f"{item.taxonomy_type}:{item.code}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _calculate_confidence(
        self,
        category_match: Optional[TaxonomyMatch],
        skill_type_match: Optional[TaxonomyMatch],
        scene_matches: List[TaxonomyMatch],
        tag_matches: List[TaxonomyMatch],
        model_matches: List[TaxonomyMatch],
    ) -> float:
        score = 0.0
        if category_match:
            score += 0.3
        if skill_type_match:
            score += 0.25
        if scene_matches:
            score += 0.2
        if len(tag_matches) >= 2:
            score += 0.15
        if model_matches:
            score += 0.1
        return round(min(score, 1.0), 2)

    def _runtime_skill_type(self, matched_code: Optional[str], fallback: Optional[str]) -> Optional[str]:
        if matched_code and matched_code in SKILL_TYPE_CODE_TO_RUNTIME:
            return SKILL_TYPE_CODE_TO_RUNTIME[matched_code]
        return fallback

    def _infer_use_cases(self, text: str) -> List[str]:
        haystack = self._strip_noisy_markdown(text).lower()
        scored: List[Tuple[str, int]] = []
        for use_case, keywords in USE_CASE_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if self._contains_keyword(haystack, keyword):
                    score += 1
            if score > 0:
                scored.append((use_case, score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return [name for name, _ in scored[:3]]

    def _infer_tags(self, text: str) -> List[str]:
        haystack = self._tag_signal_text(text).lower()
        matched: List[Tuple[str, int]] = []
        for label, keywords in TAG_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if self._contains_keyword(haystack, keyword):
                    score += 1
            if score > 0:
                matched.append((label, score))
        matched.sort(key=lambda item: (-item[1], item[0]))
        return [name for name, _ in matched[:6]]

    def _extract_tags_from_readmes(self, repo: ParsedGithubRepo) -> List[str]:
        readme_source = "\n".join(repo.readme_texts or ([repo.readme_text] if repo.readme_text else []))
        return self._infer_tags(readme_source)

    def _has_any_keyword(self, text: str, keywords: Iterable[str]) -> bool:
        return any(self._contains_keyword(text, keyword) for keyword in keywords)

    def _finance_signal_strength(self, signal_text: str) -> Tuple[int, int]:
        lowered = signal_text.lower()
        strong = sum(1 for keyword in FINANCE_STRONG_SIGNAL_KEYWORDS if self._contains_keyword(lowered, keyword))
        weak = sum(1 for keyword in FINANCE_WEAK_SIGNAL_KEYWORDS if self._contains_keyword(lowered, keyword))
        return strong, weak

    def _is_agentic_repo_context(
        self,
        *,
        signal_text: str,
        skill_type: Optional[str],
        category: Optional[str],
        use_cases: List[str],
    ) -> bool:
        lowered = signal_text.lower()
        return bool(
            skill_type in {"agent", "workflow", "prompt"}
            or category == "engineering"
            or "development" in use_cases
            or self._has_any_keyword(lowered, AGENTIC_REPO_KEYWORDS)
        )

    def _should_keep_finance_tags(
        self,
        *,
        signal_text: str,
        skill_type: Optional[str],
        category: Optional[str],
        use_cases: List[str],
    ) -> bool:
        if category != "data-business-analysis" and skill_type in {"agent", "workflow", "prompt"}:
            return False
        strong_count, weak_count = self._finance_signal_strength(signal_text)
        if strong_count >= 2:
            return True
        if strong_count >= 1 and weak_count >= 2:
            return True
        if not self._is_agentic_repo_context(
            signal_text=signal_text,
            skill_type=skill_type,
            category=category,
            use_cases=use_cases,
        ) and (strong_count >= 1 or weak_count >= 3):
            return True
        return False

    def _filter_tags(
        self,
        tags: List[str],
        *,
        category: Optional[str],
        skill_type: Optional[str],
        use_cases: List[str],
        signal_text: str,
    ) -> List[str]:
        filtered: List[str] = []
        lowered_signal = signal_text.lower()
        is_productivity_tool = (
            category == "office"
            or skill_type == "tool_config"
            or "productivity" in use_cases
        )
        keep_finance_tags = self._should_keep_finance_tags(
            signal_text=lowered_signal,
            skill_type=skill_type,
            category=category,
            use_cases=use_cases,
        )

        for tag in tags:
            if tag in HIGH_RISK_FINANCE_TAGS and not keep_finance_tags:
                continue
            if is_productivity_tool and tag in {"内容创作", "测试自动化", "视觉设计", "营销推广", "学习研究"}:
                if tag == "内容创作" and self._contains_keyword(lowered_signal, "content creation"):
                    filtered.append(tag)
                elif tag == "测试自动化" and (
                    self._contains_keyword(lowered_signal, "automated testing")
                    or self._contains_keyword(lowered_signal, "unit test")
                    or self._contains_keyword(lowered_signal, "pytest")
                ):
                    filtered.append(tag)
                else:
                    continue
            else:
                filtered.append(tag)

        deduped: List[str] = []
        seen = set()
        for item in filtered:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:8]

    def _recommend_meta(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str], List[str], List[str]]:
        haystack = text.lower()
        finance_strong, finance_weak = self._finance_signal_strength(haystack)
        has_agentic_signal = self._has_any_keyword(haystack, AGENTIC_REPO_KEYWORDS)
        if finance_strong >= 2 or (finance_strong >= 1 and finance_weak >= 2 and not has_agentic_signal):
            return "data-business-analysis", "agent", "advanced", ["投资研究", "股票研究"], ["data_analysis"]
        if any(
            word in haystack
            for word in [
                "clipboard",
                "pasteboard",
                "clipboard manager",
                "copy and paste",
                "screenshot",
                "screen capture",
                "menu bar",
                "hotkey",
                "macos",
                "swiftui",
                "desktop app",
                "floating panel",
                "always-on-top",
                "always on top",
                "粘贴板",
                "剪贴板",
                "截图",
                "菜单栏",
                "快捷键",
                "浮动面板",
            ]
        ):
            return "office", "tool_config", "beginner", ["办公提效"], ["productivity"]
        if any(word in haystack for word in ["code", "review", "testing", "architecture", "frontend", "backend"]):
            return "engineering", "workflow", "intermediate", ["代码审查", "测试自动化"], ["development", "productivity"]
        if any(word in haystack for word in ["image", "design", "visual", "poster", "canvas", "illustration"]):
            return "design-visual", "prompt", "intermediate", ["视觉设计", "图片生成", "创意设计"], ["content_creation"]
        if any(word in haystack for word in ["writing", "copy", "content", "blog", "article"]):
            return "writing-content", "prompt", "beginner", ["写作", "内容创作", "文案"], ["content_creation", "marketing"]
        return None, None, None, [], []

    def _build_parse_result(self, github_url: str) -> Tuple[GithubSkillParseOut, GithubRepoPreview]:
        parsed_url = self.parse_github_url(github_url)
        repo, skill_md_payload, readme_payload, license_payload = self._fetch_repo_bundle(parsed_url)
        repo_json = repo.raw_repo

        skill_md_text, skill_md_path, skill_md_sha = self._decode_content(skill_md_payload)
        readme_text, readme_path, readme_sha = self._decode_content(readme_payload)
        _, license_path, license_sha = self._decode_content(license_payload)

        frontmatter, skill_body = self._extract_frontmatter(skill_md_text)
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}

        frontmatter_description = str(frontmatter.get("description") or "").strip()
        repo_description = repo.description
        readme_first = self._first_paragraph(readme_text or "")
        description = self._preferred_description(
            frontmatter_description=frontmatter_description,
            skill_body=skill_body,
            readme_text=readme_text or "",
            repo_description=repo_description,
            selected_skill_path=skill_md_path,
            selected_readme_path=readme_path,
        )
        summary = (
            metadata.get("short-description")
            or metadata.get("short_description")
            or self._truncate_summary(frontmatter_description)
            or self._truncate_summary(description)
            or self._truncate_summary(readme_first)
            or self._truncate_summary(repo_description)
            or parsed_url.repo
        )
        title = str(frontmatter.get("name") or repo.name or parsed_url.repo).strip()
        merged_text = self._build_search_text(repo, title, description, frontmatter, skill_body)
        category_match = self._match_one(self._category_candidates(), merged_text, min_score=3)
        skill_type_match = self._match_one(self._skill_type_candidates(), merged_text, min_score=3)
        scene_matches = [
            item for item in self._match_many(self._tag_candidates("scene"), merged_text, min_score=2, limit=5)
            if item.code not in GENERIC_TAG_CODES
        ]
        tag_matches = [
            item for item in self._match_many(self._tag_candidates("type"), merged_text, min_score=1, limit=12)
            if item.code not in GENERIC_TAG_CODES
        ]
        model_matches = self._match_many(self._model_candidates(), merged_text, min_score=1, limit=6)
        category, skill_type, difficulty, recommended_tags, use_cases = self._recommend_meta(merged_text)
        explicit_use_cases = self._parse_frontmatter_use_cases(frontmatter)
        inferred_use_cases = self._infer_use_cases("\n".join(filter(None, [merged_text, readme_text or ""])))
        explicit_tags = self._parse_frontmatter_tags(frontmatter)
        inferred_tags = self._extract_tags_from_readmes(repo)
        prompt_role = self._extract_prompt_role(frontmatter, skill_body, title, skill_type)
        system_prompt = self._extract_system_prompt(frontmatter, skill_body)
        matched_scene_use_cases = self._scene_matches_to_use_cases(scene_matches)
        normalized_use_cases = self._normalize_use_case_candidates(
            [
                *matched_scene_use_cases,
                *explicit_use_cases,
                *use_cases,
                *inferred_use_cases,
            ]
        )
        if not normalized_use_cases:
            normalized_use_cases = inferred_use_cases or use_cases or explicit_use_cases
        final_use_cases: List[str] = []
        for item in normalized_use_cases:
            if item not in final_use_cases:
                final_use_cases.append(item)
        final_category = category_match.code if category_match else category
        resolved_skill_type = self._runtime_skill_type(
            skill_type_match.code if skill_type_match else None,
            skill_type,
        )
        final_tags: List[str] = []
        seen_tags = set()
        matched_tag_names = [item.name for item in tag_matches]
        for item in explicit_tags + inferred_tags + matched_tag_names + recommended_tags:
            cleaned = str(item or "").strip()[:50]
            lowered = cleaned.lower()
            if not cleaned or lowered in seen_tags:
                continue
            seen_tags.add(lowered)
            final_tags.append(cleaned)
        final_tags = self._filter_tags(
            final_tags,
            category=final_category,
            skill_type=resolved_skill_type,
            use_cases=final_use_cases,
            signal_text=self._tag_signal_text("\n".join(repo.readme_texts or ([repo.readme_text] if repo.readme_text else []))),
        )
        matched_taxonomies = {
            "category": [category_match.code] if category_match else ([category] if category else []),
            "skill_type": [skill_type_match.code] if skill_type_match else ([skill_type] if skill_type else []),
            "scene": final_use_cases,
            "tag": [item.code for item in tag_matches],
            "model": [item.code for item in model_matches],
        }
        suggested_taxonomies = self._generate_suggested_taxonomies(
            repo,
            tag_matches,
            model_matches,
            category_match,
            skill_type_match,
        )
        classify_confidence = self._calculate_confidence(
            category_match,
            skill_type_match,
            scene_matches,
            tag_matches,
            model_matches,
        )
        match_reasons: Dict[str, Any] = {
            "category": (
                {"code": category_match.code, "reason": category_match.reason, "score": category_match.score}
                if category_match
                else None
            ),
            "skill_type": (
                {"code": skill_type_match.code, "reason": skill_type_match.reason, "score": skill_type_match.score}
                if skill_type_match
                else None
            ),
            "scene": [
                {"code": item.code, "reason": item.reason, "score": item.score}
                for item in scene_matches
                if self._normalize_use_case_value(item.code) or self._normalize_use_case_value(item.name)
            ],
            "tag": [{"code": item.code, "reason": item.reason, "score": item.score} for item in tag_matches],
            "model": [{"code": item.code, "reason": item.reason, "score": item.score} for item in model_matches],
        }

        parsed = GithubSkillParsedOut(
            title=title,
            summary=summary,
            description=description or repo_description or readme_first or parsed_url.repo,
            category=final_category,
            skill_type=resolved_skill_type,
            difficulty=difficulty,
            tags=final_tags,
            use_cases=final_use_cases,
            models=[item.code for item in model_matches],
            prompt_role=prompt_role,
            system_prompt=system_prompt,
            matched_taxonomies=matched_taxonomies,
            suggested_taxonomies=suggested_taxonomies,
            match_reasons=match_reasons,
            classify_confidence=classify_confidence,
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
            language=repo.language,
            topics=repo.topics,
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
            parsed_title=payload.title or parsed.parsed.title,
            parsed_summary=payload.summary or parsed.parsed.summary,
            parsed_description=parsed.parsed.description,
            parsed_category=payload.category or parsed.parsed.category,
            parsed_skill_type=payload.skill_type or parsed.parsed.skill_type,
            parsed_difficulty=payload.difficulty or parsed.parsed.difficulty,
            parsed_tags=payload.tags or parsed.parsed.tags,
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
        inferred_use_cases = self._parse_frontmatter_use_cases(frontmatter)
        if not inferred_use_cases:
            inference_text = "\n".join(
                filter(
                    None,
                    [
                        item.parsed_title or "",
                        item.parsed_summary or "",
                        item.parsed_description or "",
                        item.raw_readme_preview or "",
                        item.raw_skill_md_preview or "",
                    ],
                )
            )
            inferred_use_cases = self._infer_use_cases(inference_text)
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
        self._ensure_import_tags(skill.id, item.parsed_tags or [], inferred_use_cases)
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

    def _ensure_tags(self, skill_id: UUID, names: List[str], tag_type: str) -> None:
        for name in names:
            cleaned = (name or "").strip()
            if not cleaned:
                continue
            slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", cleaned.lower()).strip("-") or cleaned
            tag = self.db.scalar(
                select(Tag).where(
                    Tag.slug == slug,
                    Tag.type == tag_type,
                    Tag.deleted_at.is_(None),
                )
            )
            if tag is None:
                tag = Tag(name=cleaned[:50], slug=slug[:80], type=tag_type, is_enabled=True)
                self.db.add(tag)
                self.db.flush()
            exists = self.db.scalar(select(SkillTag).where(SkillTag.skill_id == skill_id, SkillTag.tag_id == tag.id))
            if exists is None:
                self.db.add(SkillTag(skill_id=skill_id, tag_id=tag.id))

    def _ensure_import_tags(self, skill_id: UUID, names: List[str], use_cases: List[str]) -> None:
        self._ensure_tags(skill_id, names, "type")
        scene_names = [
            USE_CASE_LABELS.get(use_case, use_case)
            for use_case in (use_cases or [])
            if str(use_case).strip()
        ]
        self._ensure_tags(skill_id, scene_names, "scene")

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
