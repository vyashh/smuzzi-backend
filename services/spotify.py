# services/spotify.py
import time
import requests
from sqlalchemy.orm import Session
from models import Setting, Song
from services.matching import normalize, parse_filename, fuzzy_score

SPOTIFY_TOKEN_CACHE_SECONDS = 3200  # ~53 min
_last_token_cache: dict[tuple[int, str], tuple[str, float]] = {}
# key: (user_id, "app"), val: (token, expiry_ts)


def _get_cached_token(user_id: int) -> str | None:
    key = (user_id, "app")
    if key in _last_token_cache:
        token, exp = _last_token_cache[key]
        if time.time() < exp:
            return token
    return None


def get_spotify_token(db: Session, user_id: int) -> str:
    """Fetch a client credentials token for this user."""
    cid = db.query(Setting).filter(
        Setting.user_id == user_id, Setting.key == "spotify_client_id"
    ).first()
    secret = db.query(Setting).filter(
        Setting.user_id == user_id, Setting.key == "spotify_client_secret"
    ).first()
    if not cid or not secret:
        raise Exception("Missing Spotify client credentials in settings")

    cached = _get_cached_token(user_id)
    if cached:
        return cached

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(cid.value, secret.value),
        timeout=15,
    )
    data = resp.json()
    if resp.status_code != 200 or "access_token" not in data:
        raise Exception(f"Spotify auth failed: {data}")

    token = data["access_token"]
    _last_token_cache[(user_id, "app")] = (token, time.time() + SPOTIFY_TOKEN_CACHE_SECONDS)
    return token


def _spotify_search(token: str, query: str, limit: int = 10) -> list[dict]:
    r = requests.get(
        "https://api.spotify.com/v1/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": query, "type": "track", "limit": limit},
        timeout=15,
    )
    j = r.json()
    return j.get("tracks", {}).get("items", []) if r.status_code == 200 else []


def _score_candidate(guess_title: str, guess_artist: str | None, guess_duration_s: int | None, item: dict) -> float:
    sp_title = item.get("name") or ""
    sp_artists = ", ".join([a["name"] for a in item.get("artists", [])]) if item.get("artists") else ""
    sp_ms = item.get("duration_ms") or 0
    sp_s = int(sp_ms / 1000)

    # Fuzzy title score (weight high)
    title_score = fuzzy_score(guess_title, sp_title)

    # Artist score if we have a guess
    artist_score = fuzzy_score(guess_artist, sp_artists) if guess_artist else 0

    # Duration closeness (±2s → full points, then decay)
    dur_bonus = 0
    if guess_duration_s and sp_s:
        diff = abs(guess_duration_s - sp_s)
        if diff <= 2:
            dur_bonus = 20
        elif diff <= 5:
            dur_bonus = 10
        elif diff <= 10:
            dur_bonus = 5

    total = (0.7 * title_score) + (0.2 * artist_score) + dur_bonus
    return total


def _search_spotify_best_match(db: Session, user_id: int, title_guess: str, artist_guess: str | None, duration_s: int | None) -> dict | None:
    """Returns best Spotify track item dict or None."""
    token = get_spotify_token(db, user_id)

    queries = []
    t = normalize(title_guess)
    a = normalize(artist_guess) if artist_guess else None

    if a:
        queries.append(f'track:"{t}" artist:"{a}"')
        queries.append(f'{a} {t}')
    queries.append(f'track:"{t}"')

    best = None
    best_score = -1

    for q in queries:
        items = _spotify_search(token, q, limit=10)
        for it in items:
            sc = _score_candidate(title_guess, artist_guess, duration_s, it)
            if sc > best_score:
                best_score = sc
                best = it
        if best_score >= 90:
            break

    if best and best_score >= 80:
        best["_smuzzi_score"] = best_score
        return best
    return None


def enrich_song_from_spotify(db: Session, song: Song, user_id: int) -> bool:
    """
    Try to fill artist/title/album/duration/cover_url/spotify_id using Spotify.
    Returns True if updated, False if left unchanged.
    """
    title_guess = song.title or ""
    artist_guess = song.artist
    if not title_guess or title_guess.lower() in {"unknown", "unknown title"}:
        fname_title, fname_artist = parse_filename(song.filename)
        if fname_title:
            title_guess = fname_title
        if not artist_guess and fname_artist:
            artist_guess = fname_artist

    duration_s = song.duration if song.duration and song.duration > 0 else None
    best = _search_spotify_best_match(db, user_id, title_guess, artist_guess, duration_s)
    if not best:
        return False

    song.title = best.get("name") or song.title
    song.artist = ", ".join([a["name"] for a in best.get("artists", [])]) or song.artist
    song.album = (best.get("album") or {}).get("name") or song.album
    if best.get("duration_ms"):
        song.duration = int(best["duration_ms"] / 1000)
    if best.get("album") and best["album"].get("images"):
        song.cover_url = best["album"]["images"][0]["url"]
    song.spotify_id = best.get("id") or song.spotify_id

    db.add(song)
    db.commit()
    return True
