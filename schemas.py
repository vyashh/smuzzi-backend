from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Literal


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

class SongListOut(BaseModel):
    items: List[SongBase]
    nextCursor: Optional[int] = None
    total: Optional[int] = None  

# ------------------
# Playlists
# ------------------
class PlaylistBase(BaseModel):
    id: int
    name: str
    user_id: int
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = None


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

class LikeToggleResponse(BaseModel):
    liked: bool
    likes_count: int

ContextType = Literal["playlist", "folder", "mood", "album", "radio", "unknown"]

class PlayStartIn(BaseModel):
    track_id: int
    context_type: Optional[ContextType] = "unknown"
    context_id: Optional[str] = None
    source_label: Optional[str] = None
    position_start_sec: int = 0
    device: Optional[str] = None

class PlayEndIn(BaseModel):
    event_id: int
    position_end_sec: Optional[int] = None

# ------------------
# User
# ------------------

class UserData(BaseModel):  # renamed
    id: int
    username: str
    display_name: Optional[str] = None

    class Config:
        from_attributes = True

class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str

class DisplayNameChangeIn(BaseModel):
    display_name: str

    # ------------------
# Recent Searches
# ------------------
class RecentSearchOut(BaseModel):
    id: int
    song_id: int
    searched_at: datetime

    class Config:
        from_attributes = True

class RecentSearchCreate(BaseModel):
    song_id: int

class RecentSearchListOut(BaseModel):
    items: List[RecentSearchOut]

class SongBrief(BaseModel):
    id: int
    title: str
    artist: str | None = None
    album: str | None = None
    cover_url: str | None = None

    class Config:
        from_attributes = True

class RecentSearchWithSongOut(BaseModel):
    id: int
    searched_at: datetime
    song: SongBrief

    class Config:
        from_attributes = True

class RecentSearchWithSongListOut(BaseModel):
    items: list[RecentSearchWithSongOut]