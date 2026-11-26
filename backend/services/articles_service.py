from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import Article


def list_recent_articles(
    db: Session,
    limit: int = 6,
    category: str | None = None,
    offset: int = 0,
) -> list[Article]:
    statement = select(Article).where(Article.url != "")
    if category:
        statement = statement.where(Article.category == category)
    statement = (
        statement.order_by(Article.published_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def list_article_categories(db: Session) -> list[dict]:
    statement = (
        select(Article.category, func.count(Article.article_id))
        .where(Article.url != "")
        .group_by(Article.category)
        .order_by(func.count(Article.article_id).desc(), Article.category)
    )
    return [{"category": name, "count": count} for name, count in db.execute(statement)]
