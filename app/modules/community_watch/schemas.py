from typing import List, Optional

from pydantic import BaseModel


class CommunityWatchMeta(BaseModel):
    generatedAt: str
    source: str
    scriptVersion: int
    trendingFeedUrl: str
    githubTrendingUrl: str
    usesGithubToken: bool
    translationEnabled: bool = False
    translationModel: str = ""
    translationProvider: str = ""


class CommunityWatchFilters(BaseModel):
    since: str
    language: str
    topic: str


class CommunityWatchSummary(BaseModel):
    trackedRepositories: int
    trackedIssues: int
    trackedTopics: int
    totalStars: int
    totalForks: int
    totalStarsLabel: str
    totalForksLabel: str
    topLanguage: str
    topLanguageCount: int
    filters: CommunityWatchFilters


class CommunityWatchRepository(BaseModel):
    title: str
    fullName: str
    owner: str
    repo: str
    url: str
    description: str
    descriptionZh: str = ""
    language: str
    publishedAt: str
    source: str
    stars: int
    forks: int
    watchers: int
    openIssues: int
    starsLabel: str
    forksLabel: str
    watchersLabel: str
    topics: List[str]
    homepageUrl: Optional[str] = ""
    updatedAt: Optional[str] = ""
    pushedAt: Optional[str] = ""


class CommunityWatchIssue(BaseModel):
    title: str
    url: str
    repository: str
    commentCount: int
    commentCountLabel: str
    author: str
    createdAt: str
    updatedAt: str
    state: str
    labels: List[str]


class CommunityWatchTopic(BaseModel):
    name: str
    repoCount: int
    repoCountLabel: str
    sampleRepo: str
    sampleRepoUrl: str
    sampleRepoDescription: str
    sampleRepoDescriptionZh: str = ""


class CommunityWatchSnapshot(BaseModel):
    meta: CommunityWatchMeta
    summary: CommunityWatchSummary
    repositories: List[CommunityWatchRepository]
    issues: List[CommunityWatchIssue]
    topics: List[CommunityWatchTopic]
