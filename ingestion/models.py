from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """One cleaned news article, ready for embedding.

    Field names follow the PRD metadata table.
    """

    article_id: str          # stable ID made from the canonical URL
    title: str
    content: str             # cleaned description / full text from the feed
    publisher: str
    published_at: datetime   # ORIGINAL publication time, always UTC
    category: str
    article_url: str
    ingested_at: datetime    # when WE fetched it, always UTC
    guid: Optional[str] = None
    author: Optional[str] = None
    image_url: Optional[str] = None

    def to_dict(self):
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        data["ingested_at"] = self.ingested_at.isoformat()
        return data
