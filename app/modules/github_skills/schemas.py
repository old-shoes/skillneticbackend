from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class GithubSkillParseIn(BaseModel):
    github_url: str


class GithubSkillParsedOut(BaseModel):
    title: str
    summary: str
    description: str
    category: Optional[str] = None
    skill_type: Optional[str] = None
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    tags: List[str] = Field(default_factory=list)


class GithubSkillParseOut(BaseModel):
    repo_full_name: str
    github_url: str
    clone_url: str
    default_branch: Optional[str] = None
    repo_description: Optional[str] = None
    stars_count: int = 0
    forks_count: int = 0
    watchers_count: int = 0
    open_issues_count: int = 0
    license: Optional[str] = None
    skill_md_found: bool = False
    readme_found: bool = False
    parsed: GithubSkillParsedOut
    warnings: List[str] = Field(default_factory=list)


class GithubSkillImportCreateIn(BaseModel):
    github_url: str
    title: str
    summary: str
    category: Optional[str] = None
    skill_type: Optional[str] = None
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    tags: List[str] = Field(default_factory=list)


class GithubSkillImportCreateOut(BaseModel):
    import_id: str
    import_status: str


class GithubSkillImportListItemOut(BaseModel):
    id: str
    repo_full_name: str
    github_url: str
    import_status: str
    parsed_title: Optional[str] = None
    parsed_summary: Optional[str] = None
    parsed_category: Optional[str] = None
    parsed_skill_type: Optional[str] = None
    parsed_difficulty: Optional[str] = None
    parsed_tags: List[str] = Field(default_factory=list)
    parsed_license: Optional[str] = None
    parsed_original_author: Optional[str] = None
    duplicate_skill_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    batch_id: Optional[str] = None


class GithubSkillImportApproveIn(BaseModel):
    publish: bool = True
    is_featured: bool = False


class GithubSkillImportApproveOut(BaseModel):
    skill_id: str
    status: str


class GithubSkillImportRejectIn(BaseModel):
    reason: str


class GithubSkillSyncOut(BaseModel):
    last_synced_at: str
    stars_count: int
    forks_count: int
    github_updated_at: Optional[str] = None


class GithubSkillBatchItemIn(BaseModel):
    github_url: str
    category: Optional[str] = None
    skill_type: Optional[str] = None
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class GithubSkillBatchImportIn(BaseModel):
    mode: Literal["parse_only", "create_import", "submit_review"]
    submit_review: bool = False
    auto_publish: bool = False
    default_category: Optional[str] = None
    default_skill_type: Optional[str] = None
    default_difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    items: List[GithubSkillBatchItemIn]


class GithubSkillBatchImportItemOut(BaseModel):
    github_url: str
    repo_full_name: Optional[str] = None
    status: str
    import_id: Optional[str] = None
    skill_id: Optional[str] = None
    error_code: Optional[str] = None
    message: str


class GithubSkillBatchImportOut(BaseModel):
    batch_id: str
    total: int
    success_count: int
    failed_count: int
    duplicate_count: int
    items: List[GithubSkillBatchImportItemOut]


class GithubSkillBatchDetailOut(BaseModel):
    batch_id: str
    mode: str
    submit_review: bool
    auto_publish: bool
    default_category: Optional[str] = None
    default_skill_type: Optional[str] = None
    default_difficulty: Optional[str] = None
    total_count: int
    success_count: int
    failed_count: int
    duplicate_count: int
    created_at: Optional[str] = None
    items: List[GithubSkillImportListItemOut] = Field(default_factory=list)


class GithubRepoPreview(BaseModel):
    repo: Dict[str, Any]
    skill_md_frontmatter: Dict[str, Any]
    skill_md_preview: Optional[str] = None
    readme_preview: Optional[str] = None
