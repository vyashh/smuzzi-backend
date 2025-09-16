from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Folder, Song, User
from auth import get_current_user
import os
from mutagen import File as MutagenFile  # pip install mutagen
from services.spotify import search_spotify_track  # enrichment

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/folders")
def add_folder(
    path: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # ✅ Check if already exists for this user
    existing = db.query(Folder).filter(Folder.path == path, Folder.user_id == user.id).first()
    if existing:
        return {"id": existing.id, "path": existing.path, "message": "Already exists"}

    folder = Folder(path=path, user_id=user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "path": folder.path}


@router.get("/folders")
def list_folders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """List all registered folders for the logged-in user."""
    return db.query(Folder).filter(Folder.user_id == user.id).all()


def scan_folder(folder: Folder, db: Session, user_id: int):
    """Walk a folder, extract metadata with Mutagen, and enrich with Spotify."""
    added_songs = []

    for root, _, files in os.walk(folder.path):
        for filename in files:
            if filename.lower().endswith((".mp3", ".flac", ".wav", ".ogg")):
                file_path = os.path.join(root, filename)

                # Skip if already in DB
                existing = db.query(Song).filter_by(filename=filename, folder_id=folder.id).first()
                if existing:
                    continue

                # Local metadata via Mutagen
                audio = MutagenFile(file_path, easy=True)
                title = audio.get("title", [os.path.splitext(filename)[0]])[0] if audio else os.path.splitext(filename)[0]
                artist = audio.get("artist", ["Unknown Artist"])[0] if audio else None
                album = audio.get("album", ["Unknown Album"])[0] if audio else None
                duration = int(audio.info.length) if audio and audio.info else None

                # Create base song
                song = Song(
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    filename=filename,
                    folder_id=folder.id,
                )
                db.add(song)
                db.commit()
                db.refresh(song)

                # Try Spotify enrichment
                metadata = search_spotify_track(title, db, user_id)
                if metadata:
                    song.title = metadata["title"]
                    song.artist = metadata["artist"]
                    song.album = metadata["album"]
                    song.cover_url = metadata["cover_url"]
                    song.duration = metadata["duration"]
                    song.spotify_id = metadata["spotify_id"]
                    db.commit()

                added_songs.append(song)

    return added_songs


@router.post("/folders/{folder_id}/rescan")
def rescan_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    added_songs = scan_folder(folder, db, user.id)
    return {"message": f"Rescanned folder {folder.path}", "added": len(added_songs)}
