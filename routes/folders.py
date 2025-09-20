from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from auth import get_current_user
from database import SessionLocal
from models import Folder, Song, User
import os
from mutagen import File as MutagenFile
from mutagen import MutagenError  # for catching corrupt/unreadable files

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/folders")
def add_folder(path: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
def list_folders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List all registered folders for the current user."""
    return db.query(Folder).filter(Folder.user_id == user.id).all()


def scan_folder(folder: Folder, db: Session, user_id: int):
    """Walk a folder, extract metadata, and insert into songs."""
    added_songs = []
    for root, _, files in os.walk(folder.path):
        for filename in files:
            if filename.lower().endswith((".mp3", ".flac", ".wav", ".ogg")):
                file_path = os.path.join(root, filename)

                # Skip duplicates
                existing = db.query(Song).filter_by(filename=filename, folder_id=folder.id).first()
                if existing:
                    continue

                try:
                    audio = MutagenFile(file_path, easy=True)
                except MutagenError as e:
                    print(f"⚠️ Skipping unreadable file {file_path}: {e}")
                    continue
                except Exception as e:
                    print(f"⚠️ Unknown error reading {file_path}: {e}")
                    continue

                title = audio.get("title", [os.path.splitext(filename)[0]])[0] if audio else filename
                artist = audio.get("artist", ["Unknown Artist"])[0] if audio else None
                album = audio.get("album", ["Unknown Album"])[0] if audio else None
                duration = int(audio.info.length) if audio and audio.info else None

                song = Song(
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    filename=filename,
                    folder_id=folder.id
                )
                db.add(song)
                added_songs.append(song)

    db.commit()
    return added_songs


@router.post("/folders/{folder_id}/rescan")
def rescan_folder(folder_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Rescan an existing folder and add new songs."""
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    added_songs = scan_folder(folder, db, user.id)
    return {"message": f"Rescanned folder {folder.path}", "added": len(added_songs)}
