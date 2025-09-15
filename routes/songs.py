from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Song, Folder
import os
from schemas import SongBase
from sqlalchemy import text

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/songs", response_model=list[SongBase])
def get_songs(db: Session = Depends(get_db)):
    songs = db.query(Song).all()
    return songs


@router.get("/stream/{song_id}")
def stream_song(
    song_id: int,
    request: Request,
    range: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    # 🔹 Get song
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # 🔹 Get folder for this song
    folder = db.query(Folder).filter(Folder.id == song.folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # 🔹 Build full file path
    file_path = os.path.join(folder.path, song.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 🔹 Support Range requests
    file_size = os.path.getsize(file_path)
    start = 0
    end = file_size - 1

    if range:  # e.g. "bytes=1000-"
        match = range.replace("bytes=", "").split("-")
        start = int(match[0]) if match[0] else 0
        if match[1]:
            end = int(match[1])
    chunk_size = end - start + 1

    def iterfile(path, start: int, end: int):
        with open(path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(4096, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "audio/mpeg",
    }

    return StreamingResponse(iterfile(file_path, start, end), status_code=206, headers=headers)