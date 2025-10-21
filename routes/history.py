# routes/history.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Literal

from database import SessionLocal
from auth import get_current_user
from models import User
from services.play_events import start_event, end_event

# ---- Local request models (avoid import issues) ----
ContextType = Literal["playlist", "likes", "library", "unknown"]

class PlayStartIn(BaseModel):
    track_id: int
    context_type: Optional[ContextType] = "unknown"
    context_id: Optional[str] = None
    source_label: Optional[str] = None
    position_start_sec: int = 0
    device: Optional[str] = None

class PlayEndIn(BaseModel):
    event_id: int
    position_end_sec: Optional[int] = None
# ----------------------------------------------------

router = APIRouter(tags=["History"], prefix="/play")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/start")
def play_start(
    payload: PlayStartIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event_id = start_event(
        db=db,
        user_id=user.id,
        track_id=payload.track_id,
        context_type=payload.context_type,
        context_id=payload.context_id,
        source_label=payload.source_label,
        position_start_sec=payload.position_start_sec,
        device=payload.device,
    )
    return {"event_id": event_id}

@router.post("/end")
def play_end(
    payload: PlayEndIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    end_event(
        db=db,
        user_id=user.id,
        event_id=payload.event_id,
        position_end_sec=payload.position_end_sec,
    )
    return {"ok": True}
