from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.controllers.articles_controller import get_recent_articles
from backend.schemas.article import RecentArticle

router = APIRouter()


@router.get("/articles/recent", response_model=list[RecentArticle])
def list_recent_articles(
    limit: int = Query(default=6, ge=1, le=12),
    db: Session = Depends(get_db),
):
    return get_recent_articles(db, limit)
