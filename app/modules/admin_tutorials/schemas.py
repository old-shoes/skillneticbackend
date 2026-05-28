from datetime import datetime
from math import ceil
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


TutorialStatus = Literal["draft", "published", "offline"]
TutorialDifficulty = Literal["beginner", "intermediate", "advanced"]


class AdminPaginationOut(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int

    @classmethod
    def from_total(cls, page: int, page_size: int, total: int) -> "AdminPaginationOut":
        total_pages = ceil(total / page_size) if total > 0 else 0
        return cls(page=page, pageSize=page_size, total=total, totalPages=total_pages)


class AdminTutorialTagOut(BaseModel):
    id: str
    name: str
    slug: str


class AdminTutorialCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    color: str
    description: str
    group: Optional[str] = None
    scene: Optional[str] = None
    difficulty: Optional[TutorialDifficulty] = None
    tutorialCount: int
    skillCount: int
    isHot: bool
    isEnabled: bool
    sortOrder: int
    createdAt: datetime
    updatedAt: datetime


class AdminTutorialCategoryListOut(BaseModel):
    list: List[AdminTutorialCategoryOut]
    pagination: AdminPaginationOut


class AdminTutorialCategoryStatsOut(BaseModel):
    totalCategories: int
    enabledCategories: int
    disabledCategories: int
    totalTutorials: int


class AdminTutorialCategorySortItemIn(BaseModel):
    id: str
    sortOrder: int = Field(ge=0)


class AdminTutorialCategorySortIn(BaseModel):
    items: List[AdminTutorialCategorySortItemIn]


class AdminTutorialCategoryQueryIn(BaseModel):
    q: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, pattern=r"^(enabled|disabled)$")
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)


class AdminTutorialListItemOut(BaseModel):
    id: str
    title: str
    slug: str
    coverImage: Optional[str] = None
    category: Optional[AdminTutorialCategoryOut] = None
    tags: List[AdminTutorialTagOut]
    difficulty: TutorialDifficulty
    readTimeMinutes: int
    viewCount: int
    favoriteCount: int
    status: TutorialStatus
    isFeatured: bool
    isBeginner: bool
    updatedAt: datetime
    publishedAt: Optional[datetime] = None


class AdminTutorialListOut(BaseModel):
    list: List[AdminTutorialListItemOut]
    pagination: AdminPaginationOut


class AdminPromptBlockIn(BaseModel):
    id: Optional[str] = None
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=255)
    content: str = Field(min_length=1)
    sortOrder: int = Field(default=0, ge=0)


class AdminPromptBlockOut(AdminPromptBlockIn):
    id: str


class AdminTutorialDetailOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    contentMarkdown: str
    coverImage: Optional[str] = None
    coverIcon: Optional[str] = None
    categoryId: str
    tagIds: List[str]
    difficulty: TutorialDifficulty
    readTimeMinutes: int
    learningPoints: List[str]
    suitableFor: List[str]
    promptBlocks: List[AdminPromptBlockOut]
    seoTitle: Optional[str] = None
    seoDescription: Optional[str] = None
    status: TutorialStatus
    isFeatured: bool
    isBeginner: bool
    publishedAt: Optional[datetime] = None
    updatedAt: datetime


class AdminTutorialSaveIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=180, pattern=r"^[a-z0-9-]+$")
    summary: str = Field(min_length=1, max_length=500)
    contentMarkdown: str = Field(default="")
    categoryId: str
    tagIds: List[str] = []
    difficulty: TutorialDifficulty = "beginner"
    readTimeMinutes: int = Field(default=10, ge=1)
    coverImage: Optional[str] = Field(default=None, max_length=500)
    coverIcon: Optional[str] = Field(default=None, max_length=80)
    learningPoints: List[str] = []
    suitableFor: List[str] = []
    promptBlocks: List[AdminPromptBlockIn] = []
    seoTitle: Optional[str] = Field(default=None, max_length=160)
    seoDescription: Optional[str] = Field(default=None, max_length=300)
    isFeatured: bool = False
    isBeginner: bool = False
    status: TutorialStatus = "draft"


class AdminTutorialQueryIn(BaseModel):
    q: Optional[str] = Field(default=None, max_length=100)
    categoryId: Optional[str] = None
    tagId: Optional[str] = None
    status: Optional[TutorialStatus] = None
    difficulty: Optional[TutorialDifficulty] = None
    isFeatured: Optional[bool] = None
    publishedFrom: Optional[str] = None
    publishedTo: Optional[str] = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=50)


class AdminTutorialCategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=20)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    icon: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#2563EB", max_length=50)
    description: str = Field(default="", max_length=255)
    group: Optional[str] = Field(default=None, max_length=80)
    scene: Optional[str] = Field(default=None, max_length=80)
    difficulty: Optional[TutorialDifficulty] = None
    sortOrder: int = Field(default=0, ge=0)
    isHot: bool = False
    isEnabled: bool = True


class AdminTutorialTagIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    sortOrder: int = Field(default=0, ge=0)
    isEnabled: bool = True
    isHot: bool = False


class AdminTutorialTagListItemOut(BaseModel):
    id: str
    name: str
    slug: str
    tutorialCount: int
    isHot: bool
    isEnabled: bool
    sortOrder: int
    createdAt: datetime
    updatedAt: datetime


class AdminLearningPathIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str = Field(min_length=1, max_length=255)
    icon: str = Field(min_length=1, max_length=80)
    sortOrder: int = Field(default=0, ge=0)
    isEnabled: bool = True


class AdminLearningPathOut(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    icon: str
    tutorialCount: int
    isEnabled: bool
    sortOrder: int
    createdAt: datetime
    updatedAt: datetime


class AdminOperationLogListItemOut(BaseModel):
    id: str
    operatorName: Optional[str] = None
    module: str
    action: str
    targetId: Optional[str] = None
    targetTitle: Optional[str] = None
    beforeData: Optional[dict] = None
    afterData: Optional[dict] = None
    createdAt: datetime


class AdminOperationLogQueryIn(BaseModel):
    module: Optional[str] = Field(default=None, max_length=80)
    action: Optional[str] = Field(default=None, max_length=80)
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=50)


class AdminOperationLogListOut(BaseModel):
    list: List[AdminOperationLogListItemOut]
    pagination: AdminPaginationOut
