from datetime import datetime
from math import ceil
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


SkillTagType = Literal["scene", "type"]


class AdminPaginationOut(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int

    @classmethod
    def from_total(cls, page: int, page_size: int, total: int) -> "AdminPaginationOut":
        total_pages = ceil(total / page_size) if total > 0 else 0
        return cls(page=page, pageSize=page_size, total=total, totalPages=total_pages)


class AdminSkillCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    nameEn: Optional[str] = None
    parentId: Optional[str] = None
    parentName: Optional[str] = None
    level: int
    icon: str
    color: str
    description: str
    skillCount: int
    isEnabled: bool
    isHot: bool
    sortOrder: int
    createdAt: datetime
    updatedAt: datetime


class AdminSkillCategoryListOut(BaseModel):
    list: List[AdminSkillCategoryOut]
    pagination: AdminPaginationOut


class AdminSkillCategoryStatsOut(BaseModel):
    totalCategories: int
    enabledCategories: int
    disabledCategories: int
    rootCategories: int
    childCategories: int


class AdminSkillCategoryQueryIn(BaseModel):
    q: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, pattern=r"^(enabled|disabled)$")
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=100)


class AdminSkillCategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    nameEn: Optional[str] = Field(default=None, max_length=80)
    parentId: Optional[str] = None
    icon: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#2563EB", max_length=50)
    description: str = Field(default="", max_length=255)
    sortOrder: int = Field(default=0, ge=0)
    isHot: bool = False
    isEnabled: bool = True


class AdminSkillTagOut(BaseModel):
    id: str
    name: str
    slug: str
    type: SkillTagType
    skillCount: int
    isEnabled: bool
    sortOrder: int
    createdAt: datetime
    updatedAt: datetime


class AdminSkillTagIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    type: SkillTagType
    sortOrder: int = Field(default=0, ge=0)
    isEnabled: bool = True

