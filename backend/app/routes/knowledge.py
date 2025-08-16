# backend/app/routes/knowledge.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..database import get_db
from ..models import User
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

# Initialize service
knowledge_service = KnowledgeService()

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
        
        result = await knowledge_service.query_knowledge_base(
            db=db,
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
        
        queries = await knowledge_service.get_query_history(
            db=db,
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
        success = await knowledge_service.delete_query_history(db, current_user)
        
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
        stats = await knowledge_service.get_knowledge_base_stats(db, current_user)
        
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
        success = await knowledge_service.clear_knowledge_base(db, current_user)
        
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
    Search transcriptions without generating an AI answer
    """
    try:
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer
        from ..config import settings
        
        qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        collection_name = f"user_{current_user.id}_transcriptions"
        
        # Check if collection exists
        try:
            qdrant_client.get_collection(collection_name)
        except:
            return {"results": [], "total": 0}
        
        # Create query vector
        query_vector = embedder.encode(q).tolist()
        
        # Search
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.6
        )
        
        results = []
        for result in search_results:
            # Get transcription details
            transcription_id = result.payload.get('transcription_id')
            if transcription_id:
                from ..models import Transcription
                transcription = db.query(Transcription).filter(
                    Transcription.id == transcription_id
                ).first()
                
                if transcription:
                    results.append({
                        "transcription_id": str(transcription.id),
                        "title": transcription.title,
                        "text_snippet": result.payload["text"][:200] + "..." if len(result.payload["text"]) > 200 else result.payload["text"],
                        "type": result.payload.get("type", "transcription"),
                        "confidence": result.score,
                        "created_at": transcription.created_at.isoformat()
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
            detail="Search failed"
        )