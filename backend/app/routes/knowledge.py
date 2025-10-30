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
            user=current_user,
            query=query_request.query,
            limit=query_request.limit
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
            user=current_user,
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
                query=q["query"],
                answer=q["answer"],
                confidence=q["confidence"],
                response_time_ms=q["response_time_ms"],
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
        success = await knowledge_service.delete_query_history(current_user)
        
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
        stats = await knowledge_service.get_knowledge_base_stats(current_user)
        
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
        success = await knowledge_service.clear_knowledge_base(current_user)
        
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

        # Use the knowledge service to search
        search_results = await knowledge_service.search_vectors(
            user=current_user,
            query=q,
            limit=limit
        )

        results = []
        for result in search_results:
            results.append({
                "transcription_id": str(result["transcription_id"]),
                "title": result.get("title", "Untitled"),
                "text_snippet": result["text"][:200] + "..." if len(result["text"]) > 200 else result["text"],
                "type": result.get("type", "chunk"),
                "confidence": result["similarity"],
                "created_at": result.get("created_at", "")
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
        collection_name = f"user_{current_user.id}_transcriptions"
        
        debug_info = {
            "user_id": str(current_user.id),
            "collection_name": collection_name,
            "service_status": {
                "qdrant_available": knowledge_service.qdrant_available,
                "embedder_available": knowledge_service.embedder_available,
                "groq_available": knowledge_service.groq_available
            }
        }
        
        # Check Qdrant collection
        if knowledge_service.qdrant_available:
            try:
                collection_info = knowledge_service.qdrant_client.get_collection(collection_name)
                debug_info["qdrant_status"] = {
                    "collection_exists": True,
                    "points_count": collection_info.points_count,
                    "vectors_count": collection_info.vectors_count
                }
                
                # Get a sample of points
                if collection_info.points_count > 0:
                    sample_points = knowledge_service.qdrant_client.scroll(
                        collection_name=collection_name,
                        limit=3,
                        with_payload=True
                    )
                    debug_info["sample_points"] = [
                        {
                            "id": str(point.id),
                            "payload_keys": list(point.payload.keys()) if point.payload else [],
                            "title": point.payload.get("title") if point.payload else None,
                            "content_type": point.payload.get("content_type") if point.payload else None
                        }
                        for point in sample_points[0][:3]
                    ]
            except Exception as e:
                debug_info["qdrant_status"] = {
                    "collection_exists": False,
                    "error": str(e)
                }
        
        # Check database transcriptions
        transcriptions_with_kb = db.query(Transcription).filter(
            Transcription.user_id == current_user.id,
            Transcription.status == "completed",
            Transcription.qdrant_point_ids.isnot(None)
        ).all()
        
        debug_info["database_status"] = {
            "total_completed": db.query(Transcription).filter(
                Transcription.user_id == current_user.id,
                Transcription.status == "completed"
            ).count(),
            "with_knowledge_base": len(transcriptions_with_kb),
            "recent_transcriptions": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "has_qdrant_points": bool(t.qdrant_point_ids),
                    "qdrant_collection": t.qdrant_collection,
                    "created_at": t.created_at.isoformat()
                }
                for t in db.query(Transcription).filter(
                    Transcription.user_id == current_user.id
                ).order_by(Transcription.created_at.desc()).limit(5).all()
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
        
        result = await knowledge_service.query_knowledge_base(
            db=db,
            user=current_user,
            query=query,
            limit=3
        )
        
        return {
            "test_query": query,
            "result": result,
            "debug_info": {
                "service_available": knowledge_service.qdrant_available,
                "embedder_available": knowledge_service.embedder_available
            }
        }
        
    except Exception as e:
        logger.error(f"Test query failed: {e}")
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }