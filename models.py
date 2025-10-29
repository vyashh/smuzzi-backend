from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text, UniqueConstraint,  DateTime, Boolean, Float, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from database import Base


# ------------------
# Users
# ------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)

    folders = relationship("Folder", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    history = relationship("History", back_populates="user", cascade="all, delete-orphan")
    # NEW: likes on the user
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")


# ------------------
# Songs
# ------------------
class Song(Base):
    __tablename__ = "songs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist = Column(String)
    album = Column(String)
    duration = Column(Integer)
    filename = Column(String, nullable=False)   # just the file name
    filepath = Column(String, nullable=False)   # relative path from folder root ✅
    cover_url = Column(String, nullable=True)
    spotify_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)

    folder = relationship("Folder", back_populates="songs")
    # NEW: likes on the song
    likes = relationship("Like", back_populates="song", cascade="all, delete-orphan")


# ------------------
# Playlists
# ------------------
class Playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    description = Column(Text, nullable=True) 
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="playlists")
    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")


# ------------------
# Playlist Tracks
# ------------------
class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    order_index = Column(Integer)

    playlist = relationship("Playlist", back_populates="tracks")


# ------------------
# Favorites
# ------------------
class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="favorites")


# ------------------
# History
# ------------------
class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    played_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="history")


# ------------------
# Folders
# ------------------
class Folder(Base):
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="folders")
    songs = relationship("Song", back_populates="folder")

    __table_args__ = (
        UniqueConstraint("path", "user_id", name="uq_user_folder"),
    )


# ------------------
# Settings
# ------------------
class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ------------------
# Likes
# ------------------
class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)

    # REQUIRED foreign keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="likes")
    song = relationship("Song", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "song_id", name="uq_user_song_like"),
    )

AMS = ZoneInfo("Europe/Amsterdam")\



class PlayEvent(Base):
    __tablename__ = "play_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    context_type = Column(String, nullable=True)   # playlist|folder|mood|album|radio|unknown
    context_id = Column(String, nullable=True)
    source_label = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=AMS))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    position_start_sec = Column(Integer, nullable=False, default=0)
    position_end_sec = Column(Integer, nullable=True)
    duration_played_sec = Column(Integer, nullable=False, default=0)
    is_skip = Column(Boolean, nullable=False, default=False)
    device = Column(String, nullable=True)

Index("idx_play_events_user_started", PlayEvent.user_id, PlayEvent.started_at.desc())
Index("idx_play_events_user_track", PlayEvent.user_id, PlayEvent.track_id, PlayEvent.started_at.desc())

class CollectionEvent(Base):
    __tablename__ = "collection_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    action = Column(String, nullable=False)  # like|unlike|add|remove
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=AMS))

Index("idx_collection_events_user_created", CollectionEvent.user_id, CollectionEvent.created_at.desc())

class ContextProgress(Base):
    __tablename__ = "context_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    context_type = Column(String, nullable=False)
    context_id = Column(String, nullable=False)
    last_index = Column(Integer, nullable=True)
    last_track_id = Column(Integer, nullable=True)
    played_pct = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=AMS))

UniqueConstraint(ContextProgress.user_id, ContextProgress.context_type, ContextProgress.context_id, name="uq_user_ctx")

# ------------------
# Recent Searches
# ------------------
class RecentSearch(Base):
    __tablename__ = "recent_searches"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True)
    searched_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    song = relationship("Song")  