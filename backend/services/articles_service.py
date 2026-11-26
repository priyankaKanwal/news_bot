from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Article


def list_recent_articles(db: Session, limit: int = 6) -> list[Article]:
    statement = (
        select(Article)
        .where(Article.url != "")
        .order_by(Article.published_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
