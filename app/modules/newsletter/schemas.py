from pydantic import BaseModel, Field


class NewsletterSubscribeIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    locale: str = Field(default="zh", min_length=2, max_length=20)
    source: str = Field(default="footer", min_length=2, max_length=50)


class NewsletterSubscribeOut(BaseModel):
    email: str
    subscribed: bool = True
    alreadySubscribed: bool = False


class NewsletterDigestSendOut(BaseModel):
    subscribers: int
    delivered: int
    skipped: int = 0
    subject: str
