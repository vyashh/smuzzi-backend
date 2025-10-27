from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from schemas import UserData, PasswordChangeIn, DisplayNameChangeIn
from auth import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/me", response_model=UserData)
def get_me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return user

@router.patch("/me/password")
def change_password(
    payload: PasswordChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different")

    user.password_hash = hash_password(payload.new_password)
    merged = db.merge(user)        
    db.commit()
    return {"message": "Password updated"}

@router.patch("/me/display-name", response_model=UserData)
def change_display_name(
    payload: DisplayNameChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = payload.display_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Display name cannot be empty")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="Display name too long")

    user.display_name = name
    merged = db.merge(user)       
    db.commit()
    db.refresh(merged)            
    return merged
