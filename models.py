from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

# ------------------
# Users
# ------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # Relationships
    folders = relationship("Folder", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    history = relationship("History", back_populates="user", cascade="all, delete-orphan")


# ------------------
# Songs
# ------------------
class Song(Base):
    __tablename__ = "songs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist = Column(String)
    album = Column(String)
    duration = Column(Integer)                 # in seconds
    filename = Column(String, nullable=False)  # filename only
    cover_url = Column(String, nullable=True)
    spotify_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)  # link to folders

    # Relationships
    folder = relationship("Folder", back_populates="songs")


# ------------------
# Playlists
# ------------------
class Playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
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

    # Relationships
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

    # Relationships
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

    # Relationships
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