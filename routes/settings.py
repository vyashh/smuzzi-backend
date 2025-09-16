from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Setting
from schemas import SettingsUpdate
from auth import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Fetch settings for the logged-in user"""
    settings = db.query(Setting).filter(Setting.user_id == user["id"]).all()
    return {s.key: s.value for s in settings}


@router.post("/settings")
def set_settings(
    data: SettingsUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update or insert settings for the logged-in user"""
    updates = data.dict(exclude_unset=True)
    updated = {}

    for key, value in updates.items():
        setting = db.query(Setting).filter(
            Setting.key == key,
            Setting.user_id == user["id"]
        ).first()

        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value, user_id=user["id"])
            db.add(setting)

        updated[key] = value

    db.commit()
    return {"updated": updated}