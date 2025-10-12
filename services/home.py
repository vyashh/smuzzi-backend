# services/home.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import PlayEvent, ContextProgress, Song, Like  # Like exists in your repo

AMS = ZoneInfo("Europe/Amsterdam")

def _week_range_ams(now: datetime) -> Dict[str, str]:
    d = now.astimezone(AMS)
    monday = (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6)
    return {"start": monday.date().isoformat(), "end": sunday.date().isoformat()}

def tile_recently_played(db: Session, user_id: int, limit=10) -> Dict[str, Any]:
    evs = (db.query(PlayEvent)
           .filter(PlayEvent.user_id == user_id)
           .order_by(PlayEvent.started_at.desc())
           .limit(100).all())
    items, seen = [], set()
    last_track = None
    for ev in evs:
        if not ev.started_at:
            continue
        bucket = int(ev.started_at.timestamp() // 600)  # 10-min squash
        key = (ev.track_id, bucket)
        if last_track == ev.track_id and key in seen:
            continue
        seen.add(key)
        last_track = ev.track_id
        trk = db.query(Song).get(ev.track_id)
        if not trk:
            continue
        items.append({
            "track_id": trk.id,
            "title": trk.title,
            "artist": getattr(trk, "artist", ""),
            "album": getattr(trk, "album", ""),
            "cover_url": getattr(trk, "cover_url", None),
            "started_at": ev.started_at.isoformat(),
            "source": {"type": ev.context_type or "unknown", "name": ev.source_label},
        })
        if len(items) >= limit:
            break
    return {"type": "recently_played", "title": "Recently played", "items": items}

def tile_most_listened_last_week(db: Session, user_id: int, limit=5) -> Dict[str, Any]:
    now = datetime.now(tz=AMS)
    rng = _week_range_ams(now)
    # assume CET/CEST; using local midnight boundaries
    start = datetime.fromisoformat(rng["start"] + "T00:00:00+02:00")
    end   = datetime.fromisoformat(rng["end"]   + "T23:59:59+02:00")

    q = (db.query(
            PlayEvent.track_id.label("track_id"),
            func.sum(PlayEvent.duration_played_sec).label("seconds"),
            func.count(PlayEvent.id).label("plays"),
            func.max(PlayEvent.ended_at).label("last_played_at"),
        )
        .filter(
            PlayEvent.user_id == user_id,
            PlayEvent.started_at >= start, PlayEvent.started_at <= end,
            PlayEvent.duration_played_sec >= 30
        )
        .group_by(PlayEvent.track_id)
        .order_by(desc("seconds"))
        .limit(limit))

    items = []
    for row in q.all():
        trk = db.query(Song).get(row.track_id)
        if not trk:
            continue
        items.append({
            "kind": "track",
            "track_id": trk.id,
            "title": trk.title,
            "artist": getattr(trk, "artist", ""),
            "album": getattr(trk, "album", ""),
            "cover_url": getattr(trk, "cover_url", None),
            "play_count": int(row.plays or 0),
            "minutes_played": round((row.seconds or 0)/60, 1),
            "last_played_at": row.last_played_at.isoformat() if row.last_played_at else None
        })
    return {"type": "most_listened_last_week", "title": "Most listened last week", "items": items}

def tile_continue_listening(db: Session, user_id: int, limit=3) -> Dict[str, Any]:
    cps = (db.query(ContextProgress)
           .filter(ContextProgress.user_id == user_id,
                   ContextProgress.played_pct >= 0.10,
                   ContextProgress.played_pct <= 0.95)
           .order_by(ContextProgress.updated_at.desc())
           .limit(limit).all())
    items = []
    for c in cps:
        items.append({
            "context_type": c.context_type,
            "context_id": c.context_id,
            "name": c.context_id,  # resolve real title if you track names per context
            "cover_url": None,
            "progress": {"played_pct": round((c.played_pct or 0), 2), "last_position_index": c.last_index},
            "resume_action": {"type": "resume_context", "context_id": c.context_id}
        })
    return {"type": "continue_listening", "title": "Continue listening", "items": items}

def tile_favorites(db: Session, user_id: int, limit=8) -> Dict[str, Any]:
    likes = (db.query(Like)
             .filter(Like.user_id == user_id)
             .order_by(Like.created_at.desc())
             .limit(limit).all())
    items = []
    for lk in likes:
        trk = lk.song  # you have a relationship on Like -> Song
        if not trk:
            continue
        items.append({
            "track_id": trk.id,
            "title": trk.title,
            "artist": getattr(trk, "artist", ""),
            "cover_url": getattr(trk, "cover_url", None),
            "liked_at": lk.created_at.isoformat() if lk.created_at else None
        })
    total_likes = db.query(func.count(Like.id)).filter(Like.user_id == user_id).scalar() or 0
    return {"type": "favorites_hub", "title": "Favorites", "summary": {"tracks": total_likes}, "items": items}

def tile_newly_added(db: Session, user_id: int, limit=12) -> Dict[str, Any]:
    # Uses songs.imported_at if you added it; else returns empty list (tile hidden)
    if not hasattr(Song, "imported_at"):
        return {"type": "newly_added", "title": "New in your library", "items": []}
    q = (db.query(Song)
         .filter(Song.imported_at != None)
         .order_by(desc(Song.imported_at))
         .limit(limit))
    items = []
    for trk in q.all():
        items.append({
            "track_id": trk.id,
            "title": trk.title,
            "artist": getattr(trk, "artist", ""),
            "added_at": trk.imported_at.isoformat() if getattr(trk, "imported_at", None) else None,
            "cover_url": getattr(trk, "cover_url", None)
        })
    return {"type": "newly_added", "title": "New in your library", "items": items}

def assemble_home(db: Session, user_id: int) -> Dict[str, Any]:
    now = datetime.now(tz=AMS)
    tiles = [
        tile_recently_played(db, user_id),
        tile_most_listened_last_week(db, user_id),
        tile_continue_listening(db, user_id),
        tile_favorites(db, user_id),
        tile_newly_added(db, user_id),
    ]
    tiles = [t for t in tiles if t.get("items")]
    return {
        "version": "1.0",
        "generated_at": now.isoformat(),
        "timezone": "Europe/Amsterdam",
        "week_range": _week_range_ams(now),
        "tiles": tiles,
        "paging": {"next": None}
    }
