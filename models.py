from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text
from sqlalchemy.sql import func
from database import Base

# ------------------
# Users
# ------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


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


# ------------------
# Playlists
# ------------------
class Playlist(Base):
    __tablename__ = "playlists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())


# ------------------
# Playlist Tracks
# ------------------
class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    order_index = Column(Integer)


# ------------------
# Favorites
# ------------------
class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ------------------
# History
# ------------------
class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    played_at = Column(TIMESTAMP, server_default=func.now())


# ------------------
# Folders
# ------------------
class Folder(Base):
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(Text, nullable=False)  # absolute/relative path


# ------------------
# Settings
# ------------------
class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)