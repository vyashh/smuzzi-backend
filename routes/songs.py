from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Song
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
def stream_song(song_id: int, request: Request, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    file_path = os.path.join("music", song.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    def iterfile(file_path):
        with open(file_path, "rb") as f:
            yield from f

    return StreamingResponse(iterfile(file_path), media_type="audio/mpeg")

