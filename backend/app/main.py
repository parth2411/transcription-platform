# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, transcriptions, knowledge, users, realtime
from fastapi.responses import Response
from .routes import auth, transcriptions, knowledge, users, realtime


app = FastAPI(title="Transcription Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the realtime router
app.include_router(realtime.router, prefix="/api/transcriptions", tags=["realtime"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(transcriptions.router, prefix="/api/transcriptions", tags=["transcriptions"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(realtime.router, prefix="/api/transcriptions", tags=["realtime"])
@app.get("/")
async def root():
    return {"message": "Transcription Platform API", "version": "1.0.0"}