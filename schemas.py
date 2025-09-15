from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class SongBase(BaseModel):
    id: int
    title: str
    artist: str | None
    album: str | None
    filename: str
    cover_url: str | None
    spotify_id: str | None

    class Config:
        from_attributes = True 
        
class PlaylistBase(BaseModel):
    id: int
    name: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PlaylistCreate(BaseModel):
    name: str