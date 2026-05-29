from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


AdminRole = Literal["super_admin", "content_admin", "reviewer", "operator", "viewer"]


class AdminLoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=80)


class AdminLoginOut(BaseModel):
    accessToken: str


class AdminSessionOut(BaseModel):
    id: str
    username: str
    nickname: str
    role: AdminRole
    permissions: List[str]
    avatarUrl: Optional[str] = None


class AdminCurrentUserOut(BaseModel):
    userId: str
    username: str
    realName: str
    avatar: str
    desc: str
    homePath: str
    roles: List[str]
    token: str


class AdminSeedCredentialOut(BaseModel):
    username: str
    password: str
    created: bool
    updatedAt: datetime
