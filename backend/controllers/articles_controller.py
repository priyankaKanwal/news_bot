from sqlalchemy.orm import Session

from backend.services.articles_service import (
    list_article_categories,
    list_recent_articles,
)


def get_recent_articles(
    db: Session, limit: int = 6, category: str | None = None, offset: int = 0
):
    return list_recent_articles(db, limit, category, offset)


def get_article_categories(db: Session):
    return list_article_categories(db)
