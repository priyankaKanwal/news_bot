from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.controllers.articles_controller import (
    get_article_categories,
    get_recent_articles,
)
from backend.schemas.article import ArticleCategory, RecentArticle

router = APIRouter()


@router.get("/articles/recent", response_model=list[RecentArticle])
def list_recent_articles(
    limit: int = Query(default=6, ge=1, le=30),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    return get_recent_articles(db, limit, category, offset)


@router.get("/articles/categories", response_model=list[ArticleCategory])
def list_categories(db: Session = Depends(get_db)):
    return get_article_categories(db)
