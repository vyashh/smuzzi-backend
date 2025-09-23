from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Song, Folder, User
import os
from schemas import SongBase
from auth import get_current_user
from services.spotify import enrich_song_from_spotify
from auth import dev_or_current_user
import ffmpeg
import subprocess


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/songs", response_model=list[SongBase])
def get_songs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Song).join(Song.folder).filter(Song.folder.has(user_id=user.id)).all()


@router.get("/stream/{song_id}")
def stream_song(
    song_id: int,
    request: Request,
    range: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Stream audio to the client (always returns raw audio, no JSON)."""

    # ✅ Find song and folder
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    folder = db.query(Folder).filter(Folder.id == song.folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    file_path = song.filepath or os.path.join(folder.path, song.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # ✅ If already MP3, stream directly
    if file_path.lower().endswith(".mp3"):
        file_size = os.path.getsize(file_path)
        start, end = 0, file_size - 1

        if range:
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

    # ✅ For non-MP3 → convert to WAV in real-time
    def convert_to_wav(path):
        process = (
            ffmpeg
            .input(path)
            .output("pipe:", format="wav", acodec="pcm_s16le", ac=2, ar="44100")
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )
        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            process.stdout.close()
            process.wait()

    headers = {
        "Content-Type": "audio/wav",
        "Cache-Control": "no-cache",
    }
    return StreamingResponse(convert_to_wav(file_path), media_type="audio/wav", headers=headers)
    
@router.get("/songs/{song_id}")
def get_song(song_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    song = db.query(Song).join(Song.folder).filter(Song.id == song_id, Song.folder.has(user_id=user.id)).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.post("/songs/{song_id}/enrich")
def enrich_one(song_id: int, db: Session = Depends(get_db), user: User = Depends(dev_or_current_user)):
    song = (
        db.query(Song)
        .join(Song.folder)
        .filter(Song.id == song_id, Song.folder.has(user_id=user.id))
        .first()
    )
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    ok = enrich_song_from_spotify(db, song, user.id)
    return {"song_id": song_id, "updated": ok}


@router.post("/songs/enrich-missing")
def enrich_missing(db: Session = Depends(get_db), user: User = Depends(dev_or_current_user)):
    songs = (
        db.query(Song)
        .join(Song.folder)
        .filter(Song.folder.has(user_id=user.id), (Song.spotify_id == None))
        .all()
    )
    updated = 0
    for s in songs:
        try:
            if enrich_song_from_spotify(db, s, user.id):
                updated += 1
        except Exception as e:
            print(f"⚠️ enrich error for {s.filename}: {e}")
    return {"count": len(songs), "updated": updated}
