import requests
from sqlalchemy.orm import Session
from models import Setting

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"


def get_spotify_token(db: Session, user_id: int) -> str:
    """
    Get or refresh a Spotify access token for a given user.
    Uses the stored client_id and client_secret in the settings table.
    """

    client_id = db.query(Setting).filter_by(user_id=user_id, key="spotify_client_id").first()
    client_secret = db.query(Setting).filter_by(user_id=user_id, key="spotify_client_secret").first()

    if not client_id or not client_secret:
        raise Exception("Spotify credentials not set for this user")

    auth = (client_id.value, client_secret.value)
    data = {"grant_type": "client_credentials"}

    r = requests.post(SPOTIFY_TOKEN_URL, auth=auth, data=data)
    token_data = r.json()

    if "access_token" not in token_data:
        raise Exception(f"Spotify auth failed: {token_data}")

    # Save or update token in DB
    db.query(Setting).filter_by(user_id=user_id, key="spotify_access_token").delete()
    db.add(Setting(user_id=user_id, key="spotify_access_token", value=token_data["access_token"]))
    db.commit()

    return token_data["access_token"]


def search_spotify_track(title: str, db: Session, user_id: int) -> dict | None:
    """
    Search Spotify for a track by title.
    Returns metadata if found, otherwise None.
    """

    # Try to use existing token
    token_row = db.query(Setting).filter_by(user_id=user_id, key="spotify_access_token").first()
    token = token_row.value if token_row else get_spotify_token(db, user_id)

    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": title, "type": "track", "limit": 1}
    r = requests.get(SPOTIFY_SEARCH_URL, headers=headers, params=params)

    # If token expired → refresh once
    if r.status_code == 401:
        token = get_spotify_token(db, user_id)
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(SPOTIFY_SEARCH_URL, headers=headers, params=params)

    if r.status_code != 200:
        return None

    data = r.json()
    if not data["tracks"]["items"]:
        return None

    track = data["tracks"]["items"][0]

    return {
        "spotify_id": track["id"],
        "title": track["name"],
        "artist": track["artists"][0]["name"],
        "album": track["album"]["name"],
        "cover_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
        "duration": track["duration_ms"] // 1000  # convert ms → seconds
    }
