from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecentArticle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_id: str
    title: str
    publisher: str
    category: str
    published_at: datetime
    url: str
