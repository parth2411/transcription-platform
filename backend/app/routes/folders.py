# backend/app/routes/folders.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import logging

from ..database import get_db
from ..models import User
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

class FolderCreate(BaseModel):
    name: str
    color: Optional[str] = "#3B82F6"
    icon: Optional[str] = "folder"

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#6B7280"

@router.post("/folders")
async def create_folder(
    folder: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new folder"""
    try:
        folder_id = str(uuid4())
        db.execute(text("""
            INSERT INTO folders (id, user_id, name, color, icon, created_at)
            VALUES (:id, :user_id, :name, :color, :icon, :created_at)
        """), {
            "id": folder_id,
            "user_id": str(current_user.id),
            "name": folder.name,
            "color": folder.color,
            "icon": folder.icon,
            "created_at": datetime.utcnow()
        })
        db.commit()

        return {
            "id": folder_id,
            "name": folder.name,
            "color": folder.color,
            "icon": folder.icon,
            "transcription_count": 0
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to create folder")

@router.get("/folders")
async def list_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all folders with transcription counts"""
    try:
        folders = db.execute(text("""
            SELECT
                f.id,
                f.name,
                f.color,
                f.icon,
                f.created_at,
                COUNT(t.id) as transcription_count
            FROM folders f
            LEFT JOIN transcriptions t ON t.folder_id = f.id
            WHERE f.user_id = :user_id
            GROUP BY f.id, f.name, f.color, f.icon, f.created_at
            ORDER BY f.name ASC
        """), {"user_id": str(current_user.id)}).fetchall()

        return {
            "folders": [
                {
                    "id": row[0],
                    "name": row[1],
                    "color": row[2],
                    "icon": row[3],
                    "created_at": row[4].isoformat(),
                    "transcription_count": row[5]
                }
                for row in folders
            ]
        }

    except Exception as e:
        logger.error(f"Failed to list folders: {e}")
        raise HTTPException(status_code=500, detail="Failed to list folders")

@router.put("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    folder: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update folder details"""
    try:
        updates = []
        params = {"folder_id": folder_id, "user_id": str(current_user.id)}

        if folder.name is not None:
            updates.append("name = :name")
            params["name"] = folder.name

        if folder.color is not None:
            updates.append("color = :color")
            params["color"] = folder.color

        if folder.icon is not None:
            updates.append("icon = :icon")
            params["icon"] = folder.icon

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        db.execute(text(f"""
            UPDATE folders
            SET {", ".join(updates)}
            WHERE id = :folder_id AND user_id = :user_id
        """), params)
        db.commit()

        return {"message": "Folder updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to update folder")

@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    move_to_folder_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete folder and optionally move transcriptions"""
    try:
        # Move transcriptions if specified
        if move_to_folder_id:
            db.execute(text("""
                UPDATE transcriptions
                SET folder_id = :new_folder_id
                WHERE folder_id = :old_folder_id AND user_id = :user_id
            """), {
                "new_folder_id": move_to_folder_id,
                "old_folder_id": folder_id,
                "user_id": str(current_user.id)
            })
        else:
            # Set folder_id to NULL for transcriptions
            db.execute(text("""
                UPDATE transcriptions
                SET folder_id = NULL
                WHERE folder_id = :folder_id AND user_id = :user_id
            """), {"folder_id": folder_id, "user_id": str(current_user.id)})

        # Delete folder
        db.execute(text("""
            DELETE FROM folders
            WHERE id = :folder_id AND user_id = :user_id
        """), {"folder_id": folder_id, "user_id": str(current_user.id)})

        db.commit()
        return {"message": "Folder deleted successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete folder")

@router.post("/transcriptions/{transcription_id}/folder")
async def move_to_folder(
    transcription_id: str,
    folder_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Move transcription to folder"""
    try:
        db.execute(text("""
            UPDATE transcriptions
            SET folder_id = :folder_id
            WHERE id = :transcription_id AND user_id = :user_id
        """), {
            "folder_id": folder_id,
            "transcription_id": transcription_id,
            "user_id": str(current_user.id)
        })
        db.commit()

        return {"message": "Transcription moved successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to move transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to move transcription")

# Tags endpoints
@router.post("/tags")
async def create_tag(
    tag: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new tag"""
    try:
        tag_id = str(uuid4())
        db.execute(text("""
            INSERT INTO tags (id, user_id, name, color, created_at)
            VALUES (:id, :user_id, :name, :color, :created_at)
        """), {
            "id": tag_id,
            "user_id": str(current_user.id),
            "name": tag.name,
            "color": tag.color,
            "created_at": datetime.utcnow()
        })
        db.commit()

        return {
            "id": tag_id,
            "name": tag.name,
            "color": tag.color
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to create tag")

@router.get("/tags")
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all user tags"""
    try:
        tags = db.execute(text("""
            SELECT
                t.id,
                t.name,
                t.color,
                COUNT(tt.transcription_id) as usage_count
            FROM tags t
            LEFT JOIN transcription_tags tt ON tt.tag_id = t.id
            WHERE t.user_id = :user_id
            GROUP BY t.id, t.name, t.color
            ORDER BY usage_count DESC, t.name ASC
        """), {"user_id": str(current_user.id)}).fetchall()

        return {
            "tags": [
                {
                    "id": row[0],
                    "name": row[1],
                    "color": row[2],
                    "usage_count": row[3]
                }
                for row in tags
            ]
        }

    except Exception as e:
        logger.error(f"Failed to list tags: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tags")

@router.post("/transcriptions/{transcription_id}/tags/{tag_id}")
async def add_tag_to_transcription(
    transcription_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add tag to transcription"""
    try:
        db.execute(text("""
            INSERT INTO transcription_tags (transcription_id, tag_id)
            VALUES (:transcription_id, :tag_id)
            ON CONFLICT DO NOTHING
        """), {
            "transcription_id": transcription_id,
            "tag_id": tag_id
        })
        db.commit()

        return {"message": "Tag added successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to add tag")

@router.delete("/transcriptions/{transcription_id}/tags/{tag_id}")
async def remove_tag_from_transcription(
    transcription_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove tag from transcription"""
    try:
        db.execute(text("""
            DELETE FROM transcription_tags
            WHERE transcription_id = :transcription_id AND tag_id = :tag_id
        """), {
            "transcription_id": transcription_id,
            "tag_id": tag_id
        })
        db.commit()

        return {"message": "Tag removed successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to remove tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove tag")
