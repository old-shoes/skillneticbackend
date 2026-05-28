from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


EmailCodeScene = Literal["register", "forgot_password"]
GithubAuthIntent = Literal["login", "register"]


class AuthRegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=80)
    locale: str = Field(default="zh", max_length=20)


class AuthLoginIn(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=80)


class AuthEmailCodeSendIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    scene: EmailCodeScene


class AuthEmailCodeSendOut(BaseModel):
    cooldownSeconds: int
    debugCode: Optional[str] = None


class AuthEmailRegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    emailCode: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=8, max_length=80)
    confirmPassword: str = Field(min_length=8, max_length=80)
    agreeTerms: bool
    locale: str = Field(default="zh", max_length=20)


class AuthEmailLoginIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=80)
    rememberMe: bool = True


class AuthPasswordResetIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    emailCode: str = Field(min_length=6, max_length=6)
    newPassword: str = Field(min_length=8, max_length=80)
    confirmPassword: str = Field(min_length=8, max_length=80)


class AuthPasswordChangeIn(BaseModel):
    currentPassword: str = Field(min_length=1, max_length=80)
    newPassword: str = Field(min_length=8, max_length=80)
    confirmPassword: str = Field(min_length=8, max_length=80)


class AuthGithubLoginOut(BaseModel):
    url: str


class UserOut(BaseModel):
    id: str
    email: str
    nickname: str
    avatarUrl: Optional[str] = None
    githubConnected: bool = False
    level: str
    locale: str
    createdAt: datetime


class AuthSessionOut(BaseModel):
    token: str
    user: UserOut


class AuthActionOut(BaseModel):
    success: bool = True
