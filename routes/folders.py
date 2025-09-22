from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth import get_current_user
from database import SessionLocal
from models import Folder, Song, User
import os
from mutagen import File as MutagenFile
from mutagen import MutagenError

from services.spotify import enrich_song_from_spotify

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/folders")
def add_folder(path: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.query(Folder).filter(Folder.path == path, Folder.user_id == user.id).first()
    if existing:
        return {"id": existing.id, "path": existing.path, "message": "Already exists"}

    folder = Folder(path=path, user_id=user.id)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "path": folder.path}


@router.get("/folders")
def list_folders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Folder).filter(Folder.user_id == user.id).all()


def scan_folder(folder: Folder, db: Session, user_id: int):
    """Walk a folder, extract metadata, and insert into songs + enrich via Spotify."""
    added_songs = []
    for root, _, files in os.walk(folder.path):
        for filename in files:
            if filename.lower().endswith((".mp3", ".flac", ".wav", ".ogg")):
                file_path = os.path.abspath(os.path.join(root, filename))

                # 🔹 Check by FULL PATH (not just filename)
                existing = db.query(Song).filter_by(filepath=file_path, folder_id=folder.id).first()
                if existing:
                    continue

                # Read tags / duration
                audio = None
                try:
                    audio = MutagenFile(file_path, easy=True)
                except MutagenError as e:
                    print(f"⚠️ Skipping unreadable file {file_path}: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ Unknown error reading {file_path}: {e}")
                    continue

                title = (
                    audio.get("title", [os.path.splitext(filename)[0]])[0]
                    if audio else os.path.splitext(filename)[0]
                )
                artist = (audio.get("artist", ["Unknown Artist"])[0] if audio else None)
                album = (audio.get("album", ["Unknown Album"])[0] if audio else None)
                duration = (
                    int(audio.info.length)
                    if audio and getattr(audio, "info", None) and getattr(audio.info, "length", None)
                    else None
                )

                song = Song(
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    filename=filename,
                    filepath=file_path,   # ✅ absolute path
                    folder_id=folder.id,
                )
                db.add(song)
                db.commit()
                db.refresh(song)

                # Try to enrich with Spotify (best-effort; don’t crash scan)
                try:
                    updated = enrich_song_from_spotify(db, song, user_id)
                    if updated:
                        print(f"✅ Enriched: {song.artist} - {song.title}")
                except Exception as e:
                    print(f"⚠️ Spotify enrich failed for {filename}: {e}")

                added_songs.append(song)

    return added_songs


@router.post("/folders/{folder_id}/rescan")
def rescan_folder(folder_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    added_songs = scan_folder(folder, db, user.id)
    return {"message": f"Rescanned folder {folder.path}", "added": len(added_songs)}


@router.post("/folders/{folder_id}/rebuild")
def rebuild_folder(folder_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    updated = 0
    for song in db.query(Song).filter(Song.folder_id == folder.id).all():
        try:
            if enrich_song_from_spotify(db, song, user.id):
                updated += 1
        except Exception as e:
            print(f"⚠️ Spotify rebuild failed for {song.filename}: {e}")

    return {"message": f"Rebuilt metadata for folder {folder.path}", "updated": updated}
