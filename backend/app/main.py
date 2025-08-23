# # Update your backend/app/main.py to include WebSocket support

# from fastapi import FastAPI, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# import logging
# import os

# from .config import settings
# from .database import engine, Base
# from .routes import auth, transcriptions, knowledge, users, realtime
# from .routes import websocket  # Add this import

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
# logger = logging.getLogger(__name__)

# # Create database tables
# Base.metadata.create_all(bind=engine)

# app = FastAPI(
#     title="TranscribeAI API",
#     description="AI-powered transcription and knowledge management platform",
#     version="1.0.0"
# )

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.ALLOWED_ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Include routers
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(transcriptions.router, prefix="/api/transcriptions", tags=["Transcriptions"])
# app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])
# app.include_router(users.router, prefix="/api/users", tags=["Users"])
# app.include_router(realtime.router, prefix="/api/transcriptions", tags=["Real-time"])
# app.include_router(websocket.router, tags=["WebSocket"])  # Add WebSocket routes

# # Create uploads directory
# os.makedirs("uploads", exist_ok=True)

# # Serve uploaded files
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     try:
#         # Test database connection
#         from .database import get_db
#         db = next(get_db())
#         db.execute("SELECT 1")
#         db.close()
        
#         return {
#             "status": "healthy",
#             "database": "connected",
#             "version": "1.0.0"
#         }
#     except Exception as e:
#         logger.error(f"Health check failed: {e}")
#         return {
#             "status": "unhealthy",
#             "database": "disconnected",
#             "error": str(e)
#         }

# @app.get("/")
# async def root():
#     """Root endpoint"""
#     return {
#         "message": "TranscribeAI API",
#         "version": "1.0.0",
#         "docs": "/docs"
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, transcriptions, knowledge, users, realtime

app = FastAPI(
    title="Transcription Platform API",
    description="AI-powered transcription and knowledge base platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with proper prefixes to avoid conflicts
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(transcriptions.router, prefix="/api/transcriptions", tags=["transcriptions"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(realtime.router, prefix="/api/transcriptions", tags=["realtime"])

@app.get("/")
async def root():
    return {"message": "Transcription Platform API", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}