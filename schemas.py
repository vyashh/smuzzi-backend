from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# ------------------
# Songs
# ------------------
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


# ------------------
# Playlists
# ------------------
class PlaylistBase(BaseModel):
    id: int
    name: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PlaylistCreate(BaseModel):
    name: str


# ------------------
# Settings
# ------------------
class SettingsUpdate(BaseModel):
    theme: str | None = None
    server_url: str | None = None
    profile_picture: str | None = None


# ------------------
# Spotify Credentials
# ------------------
class SpotifyCredentials(BaseModel):
    client_id: str
    client_secret: str
