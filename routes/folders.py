from fastapi import APIRouter, Depends, HTTPException
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
def add_folder(path: str, db: Session = Depends(get_db)):
    """Register a folder and scan for songs."""
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="Folder path does not exist")

    folder = Folder(path=path)
    db.add(folder)
    db.commit()
    db.refresh(folder)

    scan_folder(folder, db)
    return {"message": "Folder added and scanned", "folder_id": folder.id}


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