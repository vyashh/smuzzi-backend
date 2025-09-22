from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
import auth  
from routes import songs, folders, playlists, settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev; restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure tables exist in smuzzi.db
Base.metadata.create_all(bind=engine)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(songs.router, prefix="/api")
app.include_router(folders.router, prefix="/api")
app.include_router(playlists.router, prefix="/api")
app.include_router(settings.router, prefix="/api")  