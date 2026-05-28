from datetime import datetime
from math import ceil
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


TutorialDifficulty = Literal["beginner", "intermediate", "advanced"]
TutorialSort = Literal["latest", "popular", "favorites"]
TutorialLocale = Literal["zh", "en"]
TutorialHelpfulVote = Literal["yes", "no"]


class TutorialQueryIn(BaseModel):
    locale: TutorialLocale = "zh"
    q: Optional[str] = Field(default=None, max_length=80)
    category: Optional[str] = Field(default=None, max_length=80)
    tag: Optional[str] = Field(default=None, max_length=80)
    sort: TutorialSort = "latest"
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=6, ge=1, le=30)


class TutorialCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    color: str
    tutorialCount: int


class TutorialTagOut(BaseModel):
    id: str
    name: str
    slug: str


class TutorialAuthorOut(BaseModel):
    id: str
    name: str
    avatarUrl: Optional[str] = None
    title: Optional[str] = None


class TutorialListItemOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    coverImage: Optional[str] = None
    coverIcon: Optional[str] = None
    category: TutorialCategoryOut
    tags: List[TutorialTagOut]
    difficulty: TutorialDifficulty
    readTimeMinutes: int
    viewCount: int
    favoriteCount: int
    publishedAt: datetime
    updatedAt: datetime
    isFeatured: bool
    isBeginner: bool


class PaginationOut(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int

    @classmethod
    def from_total(cls, page: int, page_size: int, total: int) -> "PaginationOut":
        total_pages = ceil(total / page_size) if total > 0 else 0
        return cls(page=page, pageSize=page_size, total=total, totalPages=total_pages)


class TutorialListOut(BaseModel):
    list: List[TutorialListItemOut]
    pagination: PaginationOut


class TutorialFilterOptionOut(BaseModel):
    label: str
    value: str
    icon: Optional[str] = None
    count: int = 0


class TutorialFiltersOut(BaseModel):
    categories: List[TutorialFilterOptionOut]
    hotKeywords: List[str]
    hotTags: List[TutorialFilterOptionOut]


class LearningPathOut(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    icon: str
    tutorialCount: int


class WeeklyHotTutorialOut(BaseModel):
    id: str
    title: str
    slug: str
    rank: int
    viewCount: int


class TutorialPromptBlockOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    content: str
    sortOrder: int


class TutorialRelatedItemOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: Optional[str] = None
    coverImage: Optional[str] = None
    readTimeMinutes: int
    viewCount: int


class TutorialPrevNextItemOut(BaseModel):
    title: str
    slug: str


class TutorialPrevNextOut(BaseModel):
    prev: Optional[TutorialPrevNextItemOut] = None
    next: Optional[TutorialPrevNextItemOut] = None


class TutorialDetailOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    contentMarkdown: str
    coverImage: Optional[str] = None
    coverIcon: Optional[str] = None
    category: TutorialCategoryOut
    tags: List[TutorialTagOut]
    author: TutorialAuthorOut
    difficulty: TutorialDifficulty
    readTimeMinutes: int
    viewCount: int
    favoriteCount: int
    likeCount: int
    isBeginner: bool
    publishedAt: datetime
    updatedAt: datetime
    learningPoints: List[str]
    suitableFor: List[str]
    promptBlocks: List[TutorialPromptBlockOut]
    relatedTutorials: List[TutorialRelatedItemOut]
    prevNext: TutorialPrevNextOut
    seoTitle: Optional[str] = None
    seoDescription: Optional[str] = None


class TutorialHelpfulIn(BaseModel):
    vote: TutorialHelpfulVote
