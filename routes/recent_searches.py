from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import SessionLocal
from models import RecentSearch, Song, User
from schemas import RecentSearchOut, RecentSearchCreate, RecentSearchListOut
from auth import get_current_user

router = APIRouter(prefix="/recent-searches", tags=["recent-searches"])

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=RecentSearchListOut)
def list_recent_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
):
    items = (
        db.query(RecentSearch)
        .filter(RecentSearch.user_id == current_user.id)
        .order_by(desc(RecentSearch.searched_at))
        .limit(limit)
        .all()
    )
    return {"items": items}

@router.post("", response_model=RecentSearchOut, status_code=201)
def add_recent_search(
    payload: RecentSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ensure song exists
    song = db.query(Song).filter(Song.id == payload.song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="song_not_found")

    # de-dupe by (user_id, song_id) and move to top
    existing = (
        db.query(RecentSearch)
        .filter(RecentSearch.user_id == current_user.id, RecentSearch.song_id == payload.song_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.flush()

    item = RecentSearch(user_id=current_user.id, song_id=payload.song_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{recent_id}", status_code=204)
def delete_recent_search(
    recent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = (
        db.query(RecentSearch)
        .filter(RecentSearch.id == recent_id, RecentSearch.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="not_found")
    db.delete(item)
    db.commit()
    return None
