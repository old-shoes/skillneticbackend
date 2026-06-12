from datetime import datetime
from math import ceil
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


SkillDifficulty = Literal["beginner", "intermediate", "advanced"]
SkillType = Literal["prompt", "workflow", "tutorial", "tool_config", "agent"]
SkillSort = Literal["latest", "popular", "favorites", "views"]
TagType = Literal["scene", "difficulty", "type"]


class SkillQueryIn(BaseModel):
    q: Optional[str] = Field(default=None, max_length=80)
    category: Optional[str] = Field(default=None, max_length=80)
    scene: Optional[str] = Field(default=None, max_length=80)
    type: Optional[SkillType] = None
    sort: SkillSort = "latest"
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=9, ge=1, le=30)


class CategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    color: str
    parentId: Optional[str] = None
    level: int = 1


class CategoryTreeOut(CategoryOut):
    children: List["CategoryTreeOut"] = Field(default_factory=list)


class TagOut(BaseModel):
    id: str
    name: str
    slug: str
    type: TagType


class SkillListItemOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    authorName: Optional[str] = None
    coverIcon: Optional[str] = None
    category: CategoryOut
    primaryCategory: CategoryOut
    categories: List[CategoryOut]
    tags: List[TagOut]
    difficulty: SkillDifficulty
    type: SkillType
    recommendedModels: List[str]
    favoriteCount: int
    viewCount: int
    publishedAt: datetime
    isFeatured: bool
    isHot: bool
    sourceType: str = "user"
    sourceUrl: Optional[str] = None
    sourceName: Optional[str] = None
    originalAuthor: Optional[str] = None
    license: Optional[str] = None
    runtimeLabels: List[str] = Field(default_factory=list)
    primaryRuntime: Optional[str] = None
    inferredSubtype: Optional[str] = None
    inferredLanguage: Optional[str] = None
    isFavorited: bool = False


class PaginationOut(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int

    @classmethod
    def from_total(cls, page: int, page_size: int, total: int) -> "PaginationOut":
        total_pages = ceil(total / page_size) if total > 0 else 0
        return cls(page=page, pageSize=page_size, total=total, totalPages=total_pages)


class SkillListOut(BaseModel):
    list: List[SkillListItemOut]
    pagination: PaginationOut


class SkillDetailOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    contentMarkdown: str
    authorName: Optional[str] = None
    coverIcon: Optional[str] = None
    category: CategoryOut
    primaryCategory: CategoryOut
    categories: List[CategoryOut]
    tags: List[TagOut]
    difficulty: SkillDifficulty
    type: SkillType
    useCase: Optional[str] = None
    recommendedModels: List[str]
    favoriteCount: int
    viewCount: int
    publishedAt: datetime
    updatedAt: datetime
    isFeatured: bool
    isHot: bool
    sourceType: str = "user"
    sourceUrl: Optional[str] = None
    sourceName: Optional[str] = None
    originalAuthor: Optional[str] = None
    license: Optional[str] = None
    runtimeLabels: List[str] = Field(default_factory=list)
    primaryRuntime: Optional[str] = None
    inferredSubtype: Optional[str] = None
    inferredLanguage: Optional[str] = None
    isFavorited: bool = False


class FilterOptionOut(BaseModel):
    label: str
    value: str
    count: int = 0


class SkillFiltersOut(BaseModel):
    categories: List[FilterOptionOut]
    categoryTree: List[CategoryTreeOut]
    scenes: List[FilterOptionOut]
    types: List[FilterOptionOut]
    runtimes: List[FilterOptionOut] = Field(default_factory=list)
    languages: List[FilterOptionOut] = Field(default_factory=list)
    dashboard: "SkillDashboardOut"


class SkillDashboardMetricOut(BaseModel):
    label: str
    value: str
    count: int = 0


class SkillDashboardOut(BaseModel):
    total: int = 0
    featuredTypes: List[SkillDashboardMetricOut] = Field(default_factory=list)
    hotScenes: List[SkillDashboardMetricOut] = Field(default_factory=list)
    topTools: List[SkillDashboardMetricOut] = Field(default_factory=list)


class SkillFavoriteOut(BaseModel):
    success: bool = True
    favorited: bool = True
    favoriteCount: int


CategoryTreeOut.model_rebuild()
