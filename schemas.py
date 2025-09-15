from pydantic import BaseModel

class SongBase(BaseModel):
    id: int
    title: str
    artist: str | None
    album: str | None
    filename: str
    cover_url: str | None
    spotify_id: str | None

    class Config:
        orm_mode = True