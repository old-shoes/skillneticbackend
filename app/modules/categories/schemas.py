from typing import List, Literal, Optional

from pydantic import BaseModel, Field


CategoryDifficulty = Literal["beginner", "intermediate", "advanced"]
CategorySort = Literal["default", "tutorials", "alphabetical"]


class CategorySidebarFilterOut(BaseModel):
    label: str
    value: str
    count: int = 0


class HotTagOut(BaseModel):
    id: str
    name: str
    slug: str
    count: int


class CategoryOverviewStatsOut(BaseModel):
    totalCategories: int
    totalTutorials: int
    weeklyViews: int
    weeklyFavorites: int


class CategoryOverviewOut(BaseModel):
    stats: CategoryOverviewStatsOut
    groups: List[CategorySidebarFilterOut]
    scenes: List[CategorySidebarFilterOut]
    hotTags: List[HotTagOut]


class CategoryItemOut(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    color: str
    description: str
    tutorialCount: int
    skillCount: int = 0
    sortOrder: int
    isEnabled: bool
    group: Optional[str] = None
    scene: Optional[str] = None
    difficulty: Optional[CategoryDifficulty] = None
    isHot: bool = False


class CategoryListOut(BaseModel):
    list: List[CategoryItemOut]


class CategoryListQueryIn(BaseModel):
    locale: str = Field(default="zh")
    q: Optional[str] = Field(default=None, max_length=100)
    group: Optional[str] = Field(default="all", max_length=80)
    scene: Optional[str] = Field(default=None, max_length=80)
    sort: CategorySort = "default"
