from __future__ import annotations

import argparse
import json
import logging
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import certifi

from app.core.config import settings


logger = logging.getLogger(__name__)

DEFAULT_TOPICS = ["ai", "agent", "llm", "rag", "copilot", "workflow-automation"]
TRENDING_FEED_URL = "https://github.com/trending"
GITHUB_API_BASE = "https://api.github.com"
DEEPL_DEFAULT_BASE_URL = "https://api-free.deepl.com/v2/translate"
MYMEMORY_DEFAULT_BASE_URL = "https://api.mymemory.translated.net/get"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


@dataclass
class FetchConfig:
    since: str
    language: Optional[str]
    topic: Optional[str]
    limit: int
    topics_limit: int
    issues_limit: int
    output: Path
    timeout: float
    github_token: str
    translate_to_zh: bool
    translation_provider: str
    deepl_api_key: str
    deepl_api_base_url: str
    mymemory_api_base_url: str
    mymemory_contact_email: str


def get_backend_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if parent.name == "backend":
            return parent
    raise RuntimeError("backend root not found")


def get_snapshot_path() -> Path:
    return get_backend_root() / "data" / "github-community-watch.json"


def build_trending_rss_url(config: FetchConfig) -> str:
    period = config.since
    language = (config.language or "all").strip() or "all"
    return f"https://mshibanami.github.io/GitHubTrendingRSS/{period}/{urllib.parse.quote(language)}.xml"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def request_json(url: str, *, timeout: float, token: str, accept: str = "application/vnd.github+json") -> Any:
    headers = {
        "Accept": accept,
        "User-Agent": "skillnetic-github-community-watch",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str, *, timeout: float, token: str = "", accept: str = "application/xml,text/xml,text/plain") -> str:
    headers = {
        "Accept": accept,
        "User-Agent": "skillnetic-github-community-watch",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
        return response.read().decode("utf-8")


def request_form_json(url: str, *, timeout: float, headers: Dict[str, str], payload: Dict[str, Any]) -> Any:
    data = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
    request = urllib.request.Request(url, headers=headers, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def request_query_json(url: str, *, timeout: float, params: Dict[str, Any], token: str = "") -> Any:
    query = urllib.parse.urlencode(params, doseq=True)
    return request_json(f"{url}?{query}", timeout=timeout, token=token, accept="application/json")


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def should_translate_to_zh(text: str) -> bool:
    value = text.strip()
    return bool(value) and not contains_cjk(value)


def translation_provider_enabled(config: FetchConfig) -> bool:
    provider = config.translation_provider.strip().lower()
    if not config.translate_to_zh:
        return False
    if provider == "deepl":
        return bool(config.deepl_api_key)
    if provider == "mymemory":
        return True
    return False


def translation_provider_meta(config: FetchConfig) -> Dict[str, str]:
    provider = config.translation_provider.strip().lower()
    if not translation_provider_enabled(config):
        return {"provider": "", "model": ""}
    if provider == "deepl":
        return {"provider": "deepl", "model": "DeepL"}
    if provider == "mymemory":
        return {"provider": "mymemory", "model": "MyMemory"}
    return {"provider": provider, "model": provider}


def parse_repo_link(link: str) -> Dict[str, str]:
    parsed = urllib.parse.urlparse(link)
    segments = [part for part in parsed.path.split("/") if part]
    if len(segments) >= 2:
        owner, repo = segments[0], segments[1]
        return {
            "owner": owner,
            "repo": repo,
            "full_name": f"{owner}/{repo}",
            "url": f"https://github.com/{owner}/{repo}",
        }
    return {"owner": "", "repo": "", "full_name": "", "url": link}


def extract_description(summary: str) -> str:
    value = summary.strip()
    if "<p>" in value and "</p>" in value:
        value = value.split("<p>", 1)[-1].split("</p>", 1)[0]
    return " ".join(value.replace("\n", " ").split())


def translate_texts_to_zh(texts: List[str], config: FetchConfig) -> Dict[str, str]:
    provider = config.translation_provider.strip().lower()
    if not translation_provider_enabled(config):
        return {}

    unique_texts = list(dict.fromkeys(text.strip() for text in texts if should_translate_to_zh(text)))
    if not unique_texts:
        return {}

    if provider == "mymemory":
        translated_map: Dict[str, str] = {}
        for source_text in unique_texts:
            params: Dict[str, Any] = {
                "q": source_text,
                "langpair": "en|zh-CN",
            }
            if config.mymemory_contact_email:
                params["de"] = config.mymemory_contact_email
            try:
                response = request_query_json(
                    config.mymemory_api_base_url,
                    timeout=config.timeout,
                    params=params,
                )
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:500]
                logger.warning("MyMemory translation request failed: %s %s", exc, detail)
                continue
            except urllib.error.URLError as exc:
                logger.warning("MyMemory translation request failed: %s", exc)
                continue

            value = str((response.get("responseData") or {}).get("translatedText", "")).strip()
            status = safe_int(response.get("responseStatus"))
            if status == 200 and value and not contains_cjk(source_text):
                translated_map[source_text] = value
        return translated_map

    if provider != "deepl":
        return {}

    payload: Dict[str, Any] = {
        "auth_key": config.deepl_api_key,
        "target_lang": "ZH",
        "preserve_formatting": "1",
        "text": unique_texts,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "skillnetic-github-community-watch",
    }
    try:
        response = request_form_json(config.deepl_api_base_url, timeout=config.timeout, headers=headers, payload=payload)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:500]
        logger.warning("DeepL translation request failed: %s %s", exc, detail)
        return {}
    except urllib.error.URLError as exc:
        logger.warning("DeepL translation request failed: %s", exc)
        return {}

    translations = response.get("translations", [])
    translated_map: Dict[str, str] = {}
    for source_text, translated in zip(unique_texts, translations):
        value = str(translated.get("text", "")).strip() if isinstance(translated, dict) else ""
        if value:
            translated_map[source_text] = value
    return translated_map


def fetch_trending_repositories(config: FetchConfig) -> List[Dict[str, Any]]:
    text = request_text(build_trending_rss_url(config), timeout=config.timeout)
    root = ET.fromstring(text)
    items = root.findall("./channel/item")
    repos: List[Dict[str, Any]] = []
    for item in items[: config.limit]:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()
        summary = item.findtext("description", default="").strip()
        parts = parse_repo_link(link)
        title_parts = title.split()
        language = title_parts[-1] if title_parts and title_parts[-1] not in parts["full_name"] else ""
        repos.append(
            {
                "title": title or parts["full_name"],
                "fullName": parts["full_name"],
                "owner": parts["owner"],
                "repo": parts["repo"],
                "url": parts["url"],
                "description": extract_description(summary),
                "descriptionZh": "",
                "language": language,
                "publishedAt": pub_date,
                "source": "github-trending-rss",
            }
        )
    return repos


def build_search_url(query: str, sort: str, order: str, per_page: int) -> str:
    params = urllib.parse.urlencode({"q": query, "sort": sort, "order": order, "per_page": per_page})
    return f"{GITHUB_API_BASE}/search/repositories?{params}"


def build_issue_search_url(query: str, sort: str, order: str, per_page: int) -> str:
    params = urllib.parse.urlencode({"q": query, "sort": sort, "order": order, "per_page": per_page})
    return f"{GITHUB_API_BASE}/search/issues?{params}"


def build_repo_url(full_name: str) -> str:
    return f"{GITHUB_API_BASE}/repos/{full_name}"


def enrich_repositories(config: FetchConfig, trending_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []

    for item in trending_repos:
        api_item: Dict[str, Any] = {}
        if item["fullName"]:
            try:
                payload = request_json(
                    build_repo_url(item["fullName"]),
                    timeout=config.timeout,
                    token=config.github_token,
                )
                if isinstance(payload, dict):
                    api_item = payload
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:300]
                logger.warning("Failed to fetch repository details for %s: %s %s", item["fullName"], exc, detail)
            except urllib.error.URLError as exc:
                logger.warning("Failed to fetch repository details for %s: %s", item["fullName"], exc)

        topics = api_item.get("topics", []) if isinstance(api_item, dict) else []
        language = item["language"] or (api_item.get("language") if isinstance(api_item, dict) else "") or ""
        stars = safe_int(api_item.get("stargazers_count")) if isinstance(api_item, dict) else 0
        forks = safe_int(api_item.get("forks_count")) if isinstance(api_item, dict) else 0
        open_issues = safe_int(api_item.get("open_issues_count")) if isinstance(api_item, dict) else 0
        watchers = safe_int(api_item.get("watchers_count")) if isinstance(api_item, dict) else 0
        enriched.append(
            {
                **item,
                "description": item["description"] or (api_item.get("description") if isinstance(api_item, dict) else "") or "",
                "language": language,
                "stars": stars,
                "forks": forks,
                "watchers": watchers,
                "openIssues": open_issues,
                "starsLabel": compact_number(stars),
                "forksLabel": compact_number(forks),
                "watchersLabel": compact_number(watchers),
                "topics": topics[:8] if isinstance(topics, list) else [],
                "homepageUrl": api_item.get("homepage") if isinstance(api_item, dict) else "",
                "updatedAt": api_item.get("updated_at") if isinstance(api_item, dict) else "",
                "pushedAt": api_item.get("pushed_at") if isinstance(api_item, dict) else "",
            }
        )

    translations = translate_texts_to_zh([repo["description"] for repo in enriched], config)
    for repo in enriched:
        repo["descriptionZh"] = translations.get(repo["description"], "")
    return enriched


def fetch_top_topics(config: FetchConfig, repositories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts = Counter()
    for repo in repositories:
        for topic in repo.get("topics", []):
            counts[str(topic).strip()] += 1

    selected = [name for name, _ in counts.most_common(config.topics_limit)]
    candidates = selected or DEFAULT_TOPICS[: config.topics_limit]
    rows: List[Dict[str, Any]] = []

    for topic in candidates[: config.topics_limit]:
        payload = request_json(
            build_search_url(f"topic:{topic}", "stars", "desc", 1),
            timeout=config.timeout,
            token=config.github_token,
        )
        total_count = safe_int(payload.get("total_count"))
        sample = (payload.get("items") or [{}])[0]
        rows.append(
            {
                "name": topic,
                "repoCount": total_count,
                "repoCountLabel": compact_number(total_count),
                "sampleRepo": sample.get("full_name", ""),
                "sampleRepoUrl": sample.get("html_url", ""),
                "sampleRepoDescription": sample.get("description", "") or "",
                "sampleRepoDescriptionZh": "",
            }
        )

    translations = translate_texts_to_zh([row["sampleRepoDescription"] for row in rows], config)
    for row in rows:
        row["sampleRepoDescriptionZh"] = translations.get(row["sampleRepoDescription"], "")
    return rows


def fetch_active_issues(config: FetchConfig) -> List[Dict[str, Any]]:
    parts = ["is:issue", "is:open", "comments:>20", "label:discussion"]
    if config.language:
        parts.append(config.language)
    payload = request_json(
        build_issue_search_url(" ".join(parts), "comments", "desc", config.issues_limit),
        timeout=config.timeout,
        token=config.github_token,
    )
    items = payload.get("items", [])
    rows: List[Dict[str, Any]] = []

    for item in items[: config.issues_limit]:
        repo_url = item.get("repository_url", "")
        repo_name = repo_url.replace(f"{GITHUB_API_BASE}/repos/", "") if repo_url else ""
        rows.append(
            {
                "title": item.get("title", ""),
                "url": item.get("html_url", ""),
                "repository": repo_name,
                "commentCount": safe_int(item.get("comments")),
                "commentCountLabel": compact_number(safe_int(item.get("comments"))),
                "author": (item.get("user") or {}).get("login", ""),
                "createdAt": item.get("created_at", ""),
                "updatedAt": item.get("updated_at", ""),
                "state": item.get("state", ""),
                "labels": [label.get("name", "") for label in item.get("labels", []) if isinstance(label, dict)][:6],
            }
        )
    return rows


def build_summary(repositories: List[Dict[str, Any]], topics: List[Dict[str, Any]], issues: List[Dict[str, Any]], config: FetchConfig) -> Dict[str, Any]:
    total_stars = sum(safe_int(repo.get("stars")) for repo in repositories)
    total_forks = sum(safe_int(repo.get("forks")) for repo in repositories)
    repo_languages = Counter(repo.get("language") or "Unknown" for repo in repositories)
    top_language, top_language_count = repo_languages.most_common(1)[0] if repo_languages else ("Unknown", 0)
    return {
        "trackedRepositories": len(repositories),
        "trackedIssues": len(issues),
        "trackedTopics": len(topics),
        "totalStars": total_stars,
        "totalForks": total_forks,
        "totalStarsLabel": compact_number(total_stars),
        "totalForksLabel": compact_number(total_forks),
        "topLanguage": top_language,
        "topLanguageCount": top_language_count,
        "filters": {
            "since": config.since,
            "language": config.language or "",
            "topic": config.topic or "",
        },
    }


def export_snapshot(config: FetchConfig) -> Dict[str, Any]:
    repositories = enrich_repositories(config, fetch_trending_repositories(config))
    topics = fetch_top_topics(config, repositories)
    issues = fetch_active_issues(config)
    translation_meta = translation_provider_meta(config)
    snapshot = {
        "meta": {
            "generatedAt": iso_now(),
            "source": "github-community-watch",
            "scriptVersion": 3,
            "trendingFeedUrl": build_trending_rss_url(config),
            "githubTrendingUrl": TRENDING_FEED_URL,
            "usesGithubToken": bool(config.github_token),
            "translationEnabled": translation_provider_enabled(config),
            "translationModel": translation_meta["model"],
            "translationProvider": translation_meta["provider"],
        },
        "summary": build_summary(repositories, topics, issues, config),
        "repositories": repositories,
        "issues": issues,
        "topics": topics,
    }
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def build_fetch_config_from_settings() -> FetchConfig:
    return FetchConfig(
        since=settings.community_watch_since,
        language=settings.community_watch_language.strip() or None,
        topic=settings.community_watch_topic.strip() or None,
        limit=max(1, settings.community_watch_limit),
        topics_limit=max(1, settings.community_watch_topics_limit),
        issues_limit=max(1, settings.community_watch_issues_limit),
        output=get_snapshot_path(),
        timeout=max(3.0, settings.community_watch_timeout_seconds),
        github_token=settings.github_api_token.strip(),
        translate_to_zh=settings.community_watch_translate_to_zh,
        translation_provider=settings.community_watch_translation_provider.strip() or "mymemory",
        deepl_api_key=settings.deepl_api_key.strip(),
        deepl_api_base_url=settings.deepl_api_base_url.strip() or DEEPL_DEFAULT_BASE_URL,
        mymemory_api_base_url=settings.mymemory_api_base_url.strip() or MYMEMORY_DEFAULT_BASE_URL,
        mymemory_contact_email=settings.mymemory_contact_email.strip(),
    )


def refresh_community_watch_snapshot() -> Dict[str, Any]:
    snapshot = export_snapshot(build_fetch_config_from_settings())
    logger.info("Community watch snapshot refreshed at %s", snapshot["meta"]["generatedAt"])
    return snapshot


def parse_args() -> FetchConfig:
    default_config = build_fetch_config_from_settings()
    parser = argparse.ArgumentParser(description="Export GitHub community watch data as JSON.")
    parser.add_argument("--since", choices=["daily", "weekly", "monthly"], default=default_config.since)
    parser.add_argument("--language", default=default_config.language)
    parser.add_argument("--topic", default=default_config.topic)
    parser.add_argument("--limit", type=int, default=default_config.limit)
    parser.add_argument("--topics-limit", type=int, default=default_config.topics_limit)
    parser.add_argument("--issues-limit", type=int, default=default_config.issues_limit)
    parser.add_argument("--output", default=str(default_config.output))
    parser.add_argument("--timeout", type=float, default=default_config.timeout)
    parser.add_argument("--translate-zh", action="store_true", default=default_config.translate_to_zh)
    args = parser.parse_args()
    return FetchConfig(
        since=args.since,
        language=args.language,
        topic=args.topic,
        limit=max(1, args.limit),
        topics_limit=max(1, args.topics_limit),
        issues_limit=max(1, args.issues_limit),
        output=Path(args.output),
        timeout=max(3.0, args.timeout),
        github_token=default_config.github_token,
        translate_to_zh=bool(args.translate_zh),
        translation_provider=default_config.translation_provider,
        deepl_api_key=default_config.deepl_api_key,
        deepl_api_base_url=default_config.deepl_api_base_url,
        mymemory_api_base_url=default_config.mymemory_api_base_url,
        mymemory_contact_email=default_config.mymemory_contact_email,
    )


def cli_main() -> int:
    config = parse_args()
    try:
        snapshot = export_snapshot(config)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:500]
        print(f"HTTP error: {exc.code} {exc.reason}")
        if detail:
            print(detail)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}")
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(config.output),
                "generatedAt": snapshot["meta"]["generatedAt"],
                "repositories": len(snapshot["repositories"]),
                "issues": len(snapshot["issues"]),
                "topics": len(snapshot["topics"]),
                "translationProvider": snapshot["meta"]["translationProvider"],
            },
            ensure_ascii=False,
        )
    )
    return 0
