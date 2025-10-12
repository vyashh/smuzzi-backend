# services/play_events.py
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from typing import Optional

from models import PlayEvent, ContextProgress, Song   # Song exists in your models.py

AMS = ZoneInfo("Europe/Amsterdam")
MIN_COUNT_SECONDS = 30  # or 40% of track duration if known

def start_event(
    db: Session,
    user_id: int,
    track_id: int,
    context_type: Optional[str],
    context_id: Optional[str],
    source_label: Optional[str],
    position_start_sec: int,
    device: Optional[str],
) -> int:
    ev = PlayEvent(
        user_id=user_id,
        track_id=track_id,
        context_type=context_type,
        context_id=context_id,
        source_label=source_label,
        started_at=datetime.now(tz=AMS),
        position_start_sec=position_start_sec,
        device=device,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev.id

def end_event(db: Session, user_id: int, event_id: int, position_end_sec: Optional[int]) -> None:
    ev = db.query(PlayEvent).filter(PlayEvent.id == event_id, PlayEvent.user_id == user_id).first()
    if not ev or ev.ended_at:
        return

    ev.ended_at = datetime.now(tz=AMS)
    ev.position_end_sec = position_end_sec if position_end_sec is not None else ev.position_start_sec
    ev.duration_played_sec = max(0, ev.position_end_sec - ev.position_start_sec)

    trk = db.query(Song).filter(Song.id == ev.track_id).first()
    if trk and getattr(trk, "duration_sec", None):
        ev.is_skip = ev.duration_played_sec < min(MIN_COUNT_SECONDS, int(0.4 * trk.duration_sec))
    else:
        ev.is_skip = ev.duration_played_sec < MIN_COUNT_SECONDS

    db.commit()

    # minimal context progress (used by "Continue listening")
    if ev.context_type and ev.context_id:
        cp = (db.query(ContextProgress)
                .filter(ContextProgress.user_id == user_id,
                        ContextProgress.context_type == ev.context_type,
                        ContextProgress.context_id == ev.context_id)
                .first())
        if not cp:
            cp = ContextProgress(
                user_id=user_id,
                context_type=ev.context_type,
                context_id=ev.context_id,
            )
            db.add(cp)
        cp.last_track_id = ev.track_id
        cp.updated_at = datetime.now(tz=AMS)
        db.commit()
