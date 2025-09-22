from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Setting, User
from schemas import SettingsUpdate, SpotifyCredentials
from auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    settings = db.query(Setting).filter(Setting.user_id == current_user.id).all()
    return {s.key: s.value for s in settings}


@router.post("/settings")
def set_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updates = data.dict(exclude_unset=True)
    updated = {}

    for key, value in updates.items():
        setting = db.query(Setting).filter(
            Setting.key == key,
            Setting.user_id == current_user.id
        ).first()

        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value, user_id=current_user.id)
            db.add(setting)

        updated[key] = value

    db.commit()
    return {"updated": updated}


@router.post("/spotify")
def save_spotify_credentials(
    creds: SpotifyCredentials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Setting).filter(
        Setting.user_id == current_user.id,
        Setting.key.in_(["spotify_client_id", "spotify_client_secret"])
    ).delete()

    new_settings = [
        Setting(user_id=current_user.id, key="spotify_client_id", value=creds.client_id),
        Setting(user_id=current_user.id, key="spotify_client_secret", value=creds.client_secret),
    ]
    db.add_all(new_settings)
    db.commit()

    return {"message": "Spotify credentials saved", "saved": [s.key for s in new_settings]}


@router.get("/spotify")
def get_spotify_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creds = db.query(Setting).filter(
        Setting.user_id == current_user.id,
        Setting.key.in_(["spotify_client_id", "spotify_client_secret"])
    ).all()
    return {s.key: s.value for s in creds}