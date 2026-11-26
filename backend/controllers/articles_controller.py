from sqlalchemy.orm import Session

from backend.services.articles_service import list_recent_articles


def get_recent_articles(db: Session, limit: int = 6):
    return list_recent_articles(db, limit)
