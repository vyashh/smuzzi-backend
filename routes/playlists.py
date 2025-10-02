from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Playlist, PlaylistTrack, Song, User
from schemas import PlaylistBase, PlaylistCreate, SongBase
from auth import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Payload models ----------
class SongActionPayload(BaseModel):
    song_id: int

# ---------- Create Playlist (unchanged) ----------
@router.post("/playlists", response_model=PlaylistBase)
def create_playlist(
    payload: PlaylistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = Playlist(name=payload.name, user_id=user.id)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist

# ---------- List Playlists (unchanged) ----------
@router.get("/playlists", response_model=list[PlaylistBase])
def list_playlists(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Playlist).filter(Playlist.user_id == user.id).all()

# ---------- Add Song to Playlist (CHANGED: JSON body) ----------
@router.post("/playlists/{playlist_id}/tracks")
def add_song_to_playlist(
    playlist_id: int,
    payload: SongActionPayload,                         # ← JSON body: { "song_id": ... }
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = (
        db.query(Playlist)
        .filter(Playlist.id == playlist_id, Playlist.user_id == user.id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    song = db.query(Song).filter(Song.id == payload.song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # optional de-dup check
    exists = (
        db.query(PlaylistTrack)
        .filter(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == payload.song_id,
        )
        .first()
    )
    if exists:
        return {"message": "Song already in playlist"}

    db.add(PlaylistTrack(playlist_id=playlist_id, track_id=payload.song_id))
    db.commit()
    return {"message": "Song added to playlist"}

# ---------- Remove Song from Playlist (CHANGED: JSON body) ----------
@router.delete("/playlists/{playlist_id}/tracks")
def remove_song_from_playlist(
    playlist_id: int,
    payload: SongActionPayload,                         # ← JSON body: { "song_id": ... }
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = (
        db.query(Playlist)
        .filter(Playlist.id == playlist_id, Playlist.user_id == user.id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    track = (
        db.query(PlaylistTrack)
        .filter_by(playlist_id=playlist_id, track_id=payload.song_id)
        .first()
    )
    if not track:
        raise HTTPException(status_code=404, detail="Track not in playlist")

    db.delete(track)
    db.commit()
    return {"message": "Song removed from playlist"}

# ---------- Get Songs in a Playlist (unchanged) ----------
@router.get("/playlists/{playlist_id}/tracks", response_model=list[SongBase])
def get_playlist_tracks(
    playlist_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = (
        db.query(Playlist)
        .filter(Playlist.id == playlist_id, Playlist.user_id == user.id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    tracks = (
        db.query(Song)
        .join(PlaylistTrack, PlaylistTrack.track_id == Song.id)
        .filter(PlaylistTrack.playlist_id == playlist_id)
        .all()
    )
    return tracks

# ---------- Delete Playlist (unchanged) ----------
@router.delete("/playlists/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    playlist = (
        db.query(Playlist)
        .filter(Playlist.id == playlist_id, Playlist.user_id == user.id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).delete()
    db.delete(playlist)
    db.commit()
    return {"message": "Playlist deleted"}
