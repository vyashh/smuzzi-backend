from fastapi import FastAPI
from database import Base, engine
from routes import auth, songs

app = FastAPI()

#This line ensures tables exist in smuzzi.db
Base.metadata.create_all(bind=engine)

#Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(songs.router, prefix="/api")