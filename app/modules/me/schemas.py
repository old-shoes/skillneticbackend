from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.skill_submissions.schemas import PaginationOut, SkillSubmissionListItemOut


class MeProfileUserOut(BaseModel):
    id: str
    email: str
    nickname: str
    avatarUrl: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    emailVerified: bool = False
    githubConnected: bool = False
    points: int = 0
    level: str
    locale: str
    joinedAt: datetime


class MeProfileUpdateIn(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=2, max_length=50)
    avatarUrl: Optional[str] = Field(default=None, max_length=500)
    bio: Optional[str] = Field(default=None, max_length=300)
    location: Optional[str] = Field(default=None, max_length=80)
    locale: Optional[str] = Field(default=None, max_length=20)


class MeStatsOut(BaseModel):
    favoriteCount: int = 0
    submissionCount: int = 0
    pendingReviewCount: int = 0
    helpPostCount: int = 0


class PointRuleOut(BaseModel):
    label: str
    points: int


class MePointSummaryOut(BaseModel):
    currentPoints: int = 0
    rules: dict


class MePointLogOut(BaseModel):
    id: str
    eventType: str
    pointsChange: int
    pointsBefore: int
    pointsAfter: int
    description: Optional[str] = None
    relatedType: Optional[str] = None
    relatedId: Optional[str] = None
    createdAt: datetime


class MePointLogListOut(BaseModel):
    list: List[MePointLogOut]
    pagination: PaginationOut


class MeNotificationOut(BaseModel):
    id: str
    type: str
    title: str
    content: Optional[str] = None
    isRead: bool = False
    createdAt: datetime
    relatedType: Optional[str] = None
    relatedId: Optional[str] = None


class MeNotificationListOut(BaseModel):
    list: List[MeNotificationOut]
    pagination: PaginationOut


class MeSecurityOut(BaseModel):
    emailVerified: bool = False
    githubConnected: bool = False
    hasPassword: bool = True
    lastLoginAt: Optional[datetime] = None
    lastLoginIp: Optional[str] = None


class MeFavoriteItemOut(BaseModel):
    targetId: str
    title: str
    summary: str
    slug: Optional[str] = None
    categoryName: Optional[str] = None
    favoritedAt: datetime


class MeFavoriteListOut(BaseModel):
    list: List[MeFavoriteItemOut]
    pagination: PaginationOut


class MeOverviewOut(BaseModel):
    user: MeProfileUserOut
    stats: MeStatsOut
    pointSummary: MePointSummaryOut
    recentNotifications: List[MeNotificationOut]
    recentSubmissions: List[SkillSubmissionListItemOut]


class MeActionOut(BaseModel):
    success: bool = True

