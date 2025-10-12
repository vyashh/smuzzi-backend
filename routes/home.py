# routes/home.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessionLocal
from auth import get_current_user
from models import User
from services.home import assemble_home  

router = APIRouter(tags=["Home"], prefix="")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/home")
def get_home(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return assemble_home(db, user.id)
