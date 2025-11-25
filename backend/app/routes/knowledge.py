# backend/app/routes/knowledge.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..database import get_db
from ..models import User, Transcription, KnowledgeQuery
from ..services.auth_service import get_current_user
from ..services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    folder_id: Optional[str] = None  # Filter by folder
    source_type: Optional[str] = None  # Filter by source type (meeting, upload, recording)

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float
    query_id: str

class QueryHistoryItem(BaseModel):
    id: str
    query: str
    answer: str
    confidence: Optional[float]
    response_time_ms: Optional[int]
    created_at: str
    source_count: int

class QueryHistoryResponse(BaseModel):
    queries: List[QueryHistoryItem]
    total: int
    page: int
    per_page: int

class KnowledgeStatsResponse(BaseModel):
    transcription_count: int
    vector_count: int
    query_count: int
    total_duration_hours: float
    collection_name: str

# Note: KnowledgeService is now instantiated per-request with db session

@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    query_request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query the user's knowledge base for information
    """
    try:
        if not query_request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )
        
        if len(query_request.query) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query too long. Maximum 1000 characters."
            )

        knowledge_service = KnowledgeService(db)
        result = await knowledge_service.query_knowledge_base(
            user_id=current_user.id,
            query_text=query_request.query,
            limit=query_request.limit,
            folder_id=query_request.folder_id
        )
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            confidence=result["confidence"],
            query_id=result.get("query_id", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Knowledge base query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query failed"
        )

@router.get("/history", response_model=QueryHistoryResponse)
async def get_query_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's query history with pagination
    """
    try:
        offset = (page - 1) * per_page

        knowledge_service = KnowledgeService(db)
        queries = await knowledge_service.get_query_history(
            user_id=current_user.id,
            limit=per_page,
            offset=offset
        )
        
        # Get total count for pagination
        from ..models import KnowledgeQuery
        total = db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == current_user.id
        ).count()
        
        query_items = [
            QueryHistoryItem(
                id=q["id"],
                query=q["query_text"],
                answer=q["response_text"],
                confidence=q["confidence_score"],
                response_time_ms=q.get("response_time_ms"),
                created_at=q["created_at"],
                source_count=q["source_count"]
            )
            for q in queries
        ]
        
        return QueryHistoryResponse(
            queries=query_items,
            total=total,
            page=page,
            per_page=per_page
        )
        
    except Exception as e:
        logger.error(f"Failed to get query history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query history"
        )

@router.delete("/history")
async def clear_query_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear all query history for the user
    """
    try:
        knowledge_service = KnowledgeService(db)
        success = await knowledge_service.delete_query_history(user_id=current_user.id)
        
        if success:
            return {"message": "Query history cleared successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear query history"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear query history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear query history"
        )

@router.get("/stats", response_model=KnowledgeStatsResponse)
async def get_knowledge_base_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about user's knowledge base
    """
    try:
        knowledge_service = KnowledgeService(db)
        stats = await knowledge_service.get_knowledge_base_stats(user_id=current_user.id)
        
        return KnowledgeStatsResponse(
            transcription_count=stats["transcription_count"],
            vector_count=stats["vector_count"],
            query_count=stats["query_count"],
            total_duration_hours=stats["total_duration_hours"],
            collection_name=stats["collection_name"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get knowledge base stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )

@router.delete("/clear")
async def clear_knowledge_base(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clear entire knowledge base (vectors and query history)
    """
    try:
        knowledge_service = KnowledgeService(db)
        success = await knowledge_service.clear_knowledge_base(user_id=current_user.id)
        
        if success:
            return {"message": "Knowledge base cleared successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear knowledge base"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear knowledge base"
        )

@router.get("/search")
async def search_transcriptions(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search transcriptions without generating an AI answer (using pgvector)
    """
    try:
        knowledge_service = KnowledgeService(db)

        # Generate query embedding
        query_embedding = knowledge_service.model.encode(q).tolist()
        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Search using pgvector
        # Note: We use CAST(:query_embedding AS vector) to avoid :: syntax issues with SQLAlchemy
        search_results = db.execute(text("""
            SELECT
                tc.id,
                tc.transcription_id,
                tc.text,
                tc.chunk_index,
                t.filename,
                t.created_at,
                1 - (tc.embedding <=> CAST(:query_embedding AS vector)) as similarity
            FROM transcription_chunks tc
            JOIN transcriptions t ON t.id = tc.transcription_id
            WHERE t.user_id = :user_id
              AND tc.embedding IS NOT NULL
            ORDER BY tc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """), {
            "query_embedding": vector_str,
            "user_id": str(current_user.id),
            "limit": limit
        }).fetchall()

        results = []
        for row in search_results:
            text = row[2]
            results.append({
                "transcription_id": str(row[1]),
                "title": row[4] or "Untitled",
                "text_snippet": text[:200] + "..." if len(text) > 200 else text,
                "type": "chunk",
                "confidence": float(row[6]),
                "created_at": row[5].isoformat() if row[5] else ""
            })

        return {
            "results": results,
            "total": len(results),
            "query": q
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
    # Add these debug endpoints to your backend/app/routes/knowledge.py file
# Add at the end of the file before any existing routes

@router.get("/debug/status")
async def debug_knowledge_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check knowledge base status"""
    try:
        knowledge_service = KnowledgeService(db)

        debug_info = {
            "user_id": str(current_user.id),
            "service_status": {
                "pgvector_available": True,
                "groq_available": knowledge_service.groq_available
            }
        }

        # Check pgvector chunks
        chunk_count = db.execute(text("""
            SELECT COUNT(*) FROM transcription_chunks tc
            JOIN transcriptions t ON t.id = tc.transcription_id
            WHERE t.user_id = :user_id AND tc.embedding IS NOT NULL
        """), {"user_id": str(current_user.id)}).scalar()

        debug_info["pgvector_status"] = {
            "chunks_with_embeddings": chunk_count
        }

        # Check database transcriptions
        total_completed = db.query(Transcription).filter(
            Transcription.user_id == current_user.id,
            Transcription.status == "completed"
        ).count()

        recent_transcriptions = db.query(Transcription).filter(
            Transcription.user_id == current_user.id
        ).order_by(Transcription.created_at.desc()).limit(5).all()

        debug_info["database_status"] = {
            "total_completed": total_completed,
            "recent_transcriptions": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "status": t.status,
                    "created_at": t.created_at.isoformat()
                }
                for t in recent_transcriptions
            ]
        }

        return debug_info

    except Exception as e:
        logger.error(f"Debug status failed: {e}")
        return {"error": str(e), "error_type": type(e).__name__}

@router.post("/debug/test-query")
async def debug_test_query(
    query: str = "test query",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test a simple query to debug issues"""
    try:
        logger.info(f"Testing query: {query}")

        knowledge_service = KnowledgeService(db)
        result = await knowledge_service.query_knowledge_base(
            user_id=current_user.id,
            query_text=query,
            limit=3
        )

        return {
            "test_query": query,
            "result": result,
            "debug_info": {
                "pgvector_available": True,
                "groq_available": knowledge_service.groq_available
            }
        }

    except Exception as e:
        logger.error(f"Test query failed: {e}")
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }