from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Folder, Song
import os
from mutagen import File as MutagenFile  # pip install mutagen

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/folders")
def add_folder(path: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    # ✅ Check if already exists for this user
    existing = db.query(Folder).filter(Folder.path == path, Folder.user_id == user["id"]).first()
    if existing:
        return {"id": existing.id, "path": existing.path, "message": "Already exists"}

    folder = Folder(path=path, user_id=user["id"])
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "path": folder.path}

@router.get("/folders")
def list_folders(db: Session = Depends(get_db)):
    """List all registered folders."""
    return db.query(Folder).all()


def scan_folder(folder: Folder, db: Session):
    """Walk a folder, extract metadata, and insert into songs."""
    for root, _, files in os.walk(folder.path):
        for filename in files:
            if filename.lower().endswith((".mp3", ".flac", ".wav", ".ogg")):
                file_path = os.path.join(root, filename)

                audio = MutagenFile(file_path, easy=True)
                title = audio.get("title", [os.path.splitext(filename)[0]])[0] if audio else filename
                artist = audio.get("artist", ["Unknown Artist"])[0] if audio else None
                album = audio.get("album", ["Unknown Album"])[0] if audio else None
                duration = int(audio.info.length) if audio and audio.info else None

                # Check if song already exists (avoid duplicates)
                existing = db.query(Song).filter_by(filename=filename, folder_id=folder.id).first()
                if existing:
                    continue

                song = Song(
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    filename=filename,
                    folder_id=folder.id
                )
                db.add(song)
    db.commit()

@router.post("/folders/{folder_id}/rescan")
def rescan_folder(folder_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user["id"]).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    import os
    from mutagen import File as MutagenFile

    added_songs = []
    for root, _, files in os.walk(folder.path):
        for file in files:
            if file.endswith((".mp3", ".flac", ".wav", ".ogg")):
                filepath = os.path.join(root, file)
                # Skip if already exists
                exists = db.query(Song).filter(Song.filename == file, Song.folder_id == folder.id).first()
                if exists:
                    continue

                audio = MutagenFile(filepath, easy=True)
                title = audio.get("title", [os.path.splitext(file)[0]])[0]
                artist = audio.get("artist", ["Unknown Artist"])[0]
                album = audio.get("album", ["Unknown Album"])[0]

                song = Song(
                    title=title,
                    artist=artist,
                    album=album,
                    filename=file,
                    folder_id=folder.id,
                )
                db.add(song)
                added_songs.append(song)

    db.commit()
    return {"message": f"Rescanned folder {folder.path}", "added": len(added_songs)}
