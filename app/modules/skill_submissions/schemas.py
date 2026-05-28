from datetime import datetime
from math import ceil
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


SkillSubmitStep = Literal["basic", "prompt", "example", "review"]
SkillSubmissionStatus = Literal["draft", "pending_review", "approved", "rejected", "needs_revision", "withdrawn"]
SkillDifficulty = Literal["beginner", "intermediate", "advanced"]
SkillType = Literal["prompt", "workflow", "tutorial", "tool_config", "agent"]
SkillOutputFormat = Literal["title", "body", "tags", "interaction", "section"]
ReviewAction = Literal["submit", "approve", "reject", "request_revision", "save_review_draft", "edit_by_admin", "resubmit"]
RiskStatus = Literal["normal", "warning", "blocked", "pending"]


class SkillPromptVariableIn(BaseModel):
    id: Optional[str] = None
    name: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    placeholder: str = Field(default="", max_length=255)
    required: bool = True
    description: str = Field(default="", max_length=255)
    sortOrder: int = Field(default=0, ge=0)


class SkillExampleInputIn(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(default="", max_length=500)


class SkillExampleOutputIn(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    interactionGuide: Optional[str] = None
    rawText: Optional[str] = None


class SkillFaqIn(BaseModel):
    question: str = Field(default="", max_length=200)
    answer: str = Field(default="", max_length=1000)


class SkillSubmissionDraftIn(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=140)
    summary: Optional[str] = Field(default=None, max_length=160)
    description: Optional[str] = None
    categoryId: Optional[str] = None
    categoryIds: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    skillType: Optional[SkillType] = None
    recommendedModels: Optional[List[str]] = None
    difficulty: Optional[SkillDifficulty] = None
    estimatedTime: Optional[str] = Field(default=None, max_length=50)
    coverImage: Optional[str] = Field(default=None, max_length=500)
    useCases: Optional[List[str]] = None
    promptRole: Optional[str] = Field(default=None, max_length=100)
    promptFileName: Optional[str] = Field(default=None, max_length=255)
    systemPrompt: Optional[str] = None
    promptVariables: Optional[List[SkillPromptVariableIn]] = None
    outputFormats: Optional[List[SkillOutputFormat]] = None
    creativity: Optional[float] = Field(default=None, ge=0, le=1)
    precision: Optional[float] = Field(default=None, ge=0, le=1)
    outputLanguage: Optional[str] = Field(default=None, max_length=50)
    outputLength: Optional[str] = Field(default=None, max_length=80)
    exampleInputs: Optional[List[SkillExampleInputIn]] = None
    exampleOutput: Optional[SkillExampleOutputIn] = None
    usageGuide: Optional[str] = None
    faqs: Optional[List[SkillFaqIn]] = None
    submitNote: Optional[str] = Field(default=None, max_length=500)


class SkillSubmissionDraftCreateIn(BaseModel):
    title: str = Field(default="", max_length=100)
    summary: str = Field(default="", max_length=160)


class SkillSubmissionSubmitIn(BaseModel):
    submitNote: Optional[str] = Field(default=None, max_length=500)


class SkillSubmissionApproveIn(BaseModel):
    reviewComment: Optional[str] = Field(default=None, max_length=2000)
    publishNow: bool = True
    setFeatured: bool = False


class SkillSubmissionRejectIn(BaseModel):
    reviewComment: str = Field(min_length=1, max_length=2000)
    reasonCode: str = Field(min_length=1, max_length=80)


class SkillSubmissionRequestRevisionIn(BaseModel):
    reviewComment: str = Field(min_length=1, max_length=2000)
    requiredFields: List[str] = Field(default_factory=list)


class SkillSubmissionReviewDraftIn(BaseModel):
    reviewComment: Optional[str] = Field(default=None, max_length=2000)
    requiredFields: List[str] = Field(default_factory=list)


class SkillSubmissionQueryIn(BaseModel):
    status: Optional[SkillSubmissionStatus] = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=50)


class AdminSkillSubmissionQueryIn(BaseModel):
    q: Optional[str] = Field(default=None, max_length=100)
    status: Optional[SkillSubmissionStatus] = None
    categoryId: Optional[str] = None
    tag: Optional[str] = Field(default=None, max_length=80)
    source: Optional[str] = Field(default=None, max_length=30)
    submittedStart: Optional[str] = Field(default=None, max_length=10)
    submittedEnd: Optional[str] = Field(default=None, max_length=10)
    onlyPending: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=10, ge=1, le=50)


class SubmitterOut(BaseModel):
    id: str
    nickname: str
    avatarUrl: Optional[str] = None
    level: str = "Lv1"


class SubmissionCategoryOut(BaseModel):
    id: str
    name: str
    slug: str
    parentId: Optional[str] = None
    level: int = 1


class SubmissionCategoryTreeOut(SubmissionCategoryOut):
    children: List["SubmissionCategoryTreeOut"] = Field(default_factory=list)


class SkillSubmissionMetaOut(BaseModel):
    categories: List[SubmissionCategoryOut]
    categoryTree: List[SubmissionCategoryTreeOut]
    promptRoles: List[str]
    useCaseOptions: List[dict]
    modelOptions: List[dict]
    skillTypeOptions: List[dict]
    outputFormats: List[dict]
    difficulties: List[dict]
    revisionFieldOptions: List[dict]
    rejectReasonOptions: List[dict]


class SkillPromptVariableOut(BaseModel):
    id: str
    name: str
    label: str
    placeholder: str
    required: bool
    description: str
    sortOrder: int


class SkillReviewLogOut(BaseModel):
    id: str
    action: ReviewAction
    operatorType: str
    operatorName: Optional[str] = None
    fromStatus: Optional[str] = None
    toStatus: Optional[str] = None
    comment: Optional[str] = None
    reasonCode: Optional[str] = None
    requiredFields: List[str]
    createdAt: datetime


class SkillRiskCheckOut(BaseModel):
    id: str
    checkType: str
    status: RiskStatus
    resultMessage: Optional[str] = None
    detail: dict
    checkedAt: Optional[datetime] = None
    createdAt: datetime


class SkillSubmissionDraftOut(BaseModel):
    id: str
    title: str
    slug: Optional[str] = None
    summary: str
    description: str
    categoryId: str
    categoryIds: List[str]
    categoryName: Optional[str] = None
    tags: List[str]
    skillType: SkillType
    recommendedModels: List[str]
    difficulty: SkillDifficulty
    estimatedTime: str
    coverImage: Optional[str] = None
    useCases: List[str]
    promptRole: str
    promptFileName: Optional[str] = None
    systemPrompt: str
    promptVariables: List[SkillPromptVariableOut]
    outputFormats: List[SkillOutputFormat]
    creativity: float
    precision: float
    outputLanguage: str
    outputLength: str
    exampleInputs: List[SkillExampleInputIn]
    exampleOutput: SkillExampleOutputIn
    usageGuide: str
    faqs: List[SkillFaqIn]
    submitNote: Optional[str] = None
    status: SkillSubmissionStatus
    qualityScore: Optional[int] = None
    reviewComment: Optional[str] = None
    reviewReasonCode: Optional[str] = None
    submittedAt: Optional[datetime] = None
    reviewedAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime


class SkillSubmissionListItemOut(BaseModel):
    id: str
    title: str
    summary: str
    coverImage: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    status: SkillSubmissionStatus
    difficulty: SkillDifficulty
    category: Optional[SubmissionCategoryOut] = None
    submittedAt: Optional[datetime] = None
    updatedAt: datetime


class AdminSkillSubmissionListItemOut(BaseModel):
    id: str
    title: str
    summary: str
    coverImage: Optional[str] = None
    category: Optional[SubmissionCategoryOut] = None
    tags: List[str]
    submitter: SubmitterOut
    source: str = "user_submission"
    status: SkillSubmissionStatus
    qualityScore: Optional[int] = None
    difficulty: SkillDifficulty
    submittedAt: Optional[datetime] = None
    updatedAt: datetime


class AdminSkillSubmissionStatsOut(BaseModel):
    total: int
    pending: int
    todaySubmitted: int
    approved: int
    rejected: int
    needsRevision: int


class PaginationOut(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int

    @classmethod
    def from_total(cls, page: int, page_size: int, total: int) -> "PaginationOut":
        total_pages = ceil(total / page_size) if total > 0 else 0
        return cls(page=page, pageSize=page_size, total=total, totalPages=total_pages)


class SkillSubmissionListOut(BaseModel):
    list: List[SkillSubmissionListItemOut]
    pagination: PaginationOut


class AdminSkillSubmissionListOut(BaseModel):
    stats: AdminSkillSubmissionStatsOut
    list: List[AdminSkillSubmissionListItemOut]
    pagination: PaginationOut


class AdminSkillSubmissionDetailOut(SkillSubmissionDraftOut):
    category: Optional[SubmissionCategoryOut] = None
    submitter: SubmitterOut
    reviewLogs: List[SkillReviewLogOut]
    riskChecks: List[SkillRiskCheckOut]


SubmissionCategoryTreeOut.model_rebuild()
