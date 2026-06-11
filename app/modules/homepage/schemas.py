from typing import List, Literal, Optional

from pydantic import BaseModel


class CategoryItemOut(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    color: str
    description: str
    skillCount: int


class SkillTagOut(BaseModel):
    id: str
    name: str
    type: Literal["model", "scene", "difficulty", "type"]


class HomepageSkillOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    coverIcon: Optional[str] = None
    categoryName: str
    tags: List[SkillTagOut]
    difficulty: Literal["beginner", "intermediate", "advanced"]
    favoriteCount: int
    viewCount: int
    isFeatured: bool
    isHot: bool
    isFavorited: bool = False


class TutorialItemOut(BaseModel):
    id: str
    title: str
    slug: str
    summary: str
    coverImage: Optional[str] = None
    readTimeMinutes: int


class HomepageStatsOut(BaseModel):
    skillFavorites: int
    qualityTemplates: int
    monthlyVisits: int
    beginnerTutorials: int


class HomepageSceneCountOut(BaseModel):
    slug: str
    count: int


class HomepageActivityOut(BaseModel):
    user: str
    action: str
    target: str
    ago: str


class HomepageContributorOut(BaseModel):
    user: str
    score: int
    submissionCount: int
    favoriteCount: int


class HomepageOut(BaseModel):
    categories: List[CategoryItemOut]
    featuredSkills: List[HomepageSkillOut]
    trendingSkills: List[HomepageSkillOut]
    latestSkills: List[HomepageSkillOut]
    latestActivities: List[HomepageActivityOut]
    weeklyContributors: List[HomepageContributorOut]
    sceneCounts: List[HomepageSceneCountOut]
    tutorials: List[TutorialItemOut]
    stats: HomepageStatsOut
