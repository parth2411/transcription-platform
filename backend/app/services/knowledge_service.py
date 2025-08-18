# COMPLETE REPLACEMENT for backend/app/services/knowledge_service.py
# Copy this ENTIRE file and replace your existing knowledge_service.py

import time
import os
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from sqlalchemy import func
import uuid

from ..config import settings
from ..models import KnowledgeQuery, User, Transcription

# Fix tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        # Fix tokenizers warning
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Initialize Qdrant client with proper error handling
        try:
            self.qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=60,
                prefer_grpc=False  # This fixes the pydantic validation errors
            )
            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"✅ Qdrant connected: {len(collections.collections)} collections")
            self.qdrant_available = True
        except Exception as e:
            logger.error(f"❌ Qdrant initialization failed: {e}")
            self.qdrant_client = None
            self.qdrant_available = False
        
        # Initialize embedder
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedder initialized")
            self.embedder_available = True
        except Exception as e:
            logger.error(f"❌ Embedder initialization failed: {e}")
            self.embedder = None
            self.embedder_available = False
        
        # Initialize Groq client
        try:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("✅ Groq client initialized")
            self.groq_available = True
        except Exception as e:
            logger.error(f"❌ Groq initialization failed: {e}")
            self.groq_client = None
            self.groq_available = False

    async def query_knowledge_base(
        self, 
        db: Session, 
        user: User, 
        query: str, 
        limit: int = 5
    ) -> Dict:
        """Query the user's knowledge base and return contextual answer"""
        
        # Check if services are available
        if not self.qdrant_available:
            return {
                "answer": "Knowledge base service is currently unavailable. Please try again later.",
                "sources": [],
                "confidence": 0.0,
                "query_id": ""
            }
        
        if not self.embedder_available:
            return {
                "answer": "Text embedding service is currently unavailable. Please try again later.",
                "sources": [],
                "confidence": 0.0,
                "query_id": ""
            }
        
        try:
            start_time = time.time()
            collection_name = f"user_{user.id}_transcriptions"
            
            # Check if user has any data
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                if collection_info.points_count == 0:
                    return {
                        "answer": "No transcriptions found in your knowledge base. Please upload and process some audio files with 'Add to Knowledge Base' enabled.",
                        "sources": [],
                        "confidence": 0.0,
                        "query_id": ""
                    }
                logger.info(f"Found collection with {collection_info.points_count} points")
            except Exception as e:
                logger.warning(f"Collection not found or error: {e}")
                return {
                    "answer": "No knowledge base found. Please upload and process some audio files with 'Add to Knowledge Base' enabled.",
                    "sources": [],
                    "confidence": 0.0,
                    "query_id": ""
                }
            
            # Create query vector
            logger.info(f"Creating embedding for query: {query}")
            query_vector = self.embedder.encode(query).tolist()
            
            # Search similar content
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.3
            )
            
            logger.info(f"Found {len(search_results)} search results")
            
            if not search_results:
                return {
                    "answer": "I couldn't find relevant information in your transcriptions for this query. Try asking about topics from your uploaded content.",
                    "sources": [],
                    "confidence": 0.0,
                    "query_id": ""
                }
            
            # Prepare context for LLM
            context_parts = []
            sources = []
            
            for result in search_results:
                payload = result.payload
                logger.info(f"Processing result with score: {result.score}")
                if payload and payload.get("full_text"):
                    context_parts.append(payload["full_text"])
                    sources.append({
                        "title": payload.get("title", "Untitled"),
                        "content_type": payload.get("content_type", "unknown"),
                        "confidence": float(result.score),
                        "created_at": payload.get("created_at", "")
                    })
            
            if not context_parts:
                return {
                    "answer": "Found relevant transcriptions but could not extract content. This might be a data storage issue.",
                    "sources": sources,
                    "confidence": 0.0,
                    "query_id": ""
                }
            
            # Generate contextual answer using Groq
            if self.groq_available:
                context = "\n\n".join(context_parts)
                
                prompt = f"""
                Based on the following transcriptions from the user's knowledge base, answer their question accurately and helpfully.
                
                User's Question: {query}
                
                Relevant Transcriptions:
                {context}
                
                Please provide a comprehensive answer based on the content above. If the transcriptions don't contain enough information to fully answer the question, mention what information is available and what might be missing.
                """
                
                try:
                    response = self.groq_client.chat.completions.create(
                        model="mixtral-8x7b-32768",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    
                    answer = response.choices[0].message.content
                    confidence = min(sum(s["confidence"] for s in sources) / len(sources), 1.0)
                    
                except Exception as e:
                    logger.error(f"Groq API error: {e}")
                    answer = f"Found {len(sources)} relevant transcription(s) but could not generate a comprehensive answer due to AI service unavailability."
                    confidence = 0.5
            else:
                answer = f"Found {len(sources)} relevant transcription(s). AI summarization is currently unavailable."
                confidence = 0.5
            
            # Store query in database
            query_id = str(uuid.uuid4())
            query_record = KnowledgeQuery(
                id=query_id,
                user_id=user.id,
                query=query,
                answer=answer,
                confidence=confidence,
                response_time_ms=int((time.time() - start_time) * 1000),
                source_count=len(sources)
            )
            db.add(query_record)
            db.commit()
            
            logger.info(f"Query completed successfully with {len(sources)} sources")
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "query_id": query_id
            }
            
        except Exception as e:
            logger.error(f"Knowledge base query failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "answer": "An error occurred while searching your knowledge base. Please try again later.",
                "sources": [],
                "confidence": 0.0,
                "query_id": ""
            }

    async def get_knowledge_base_stats(self, db: Session, user: User) -> Dict:
        """Get statistics about user's knowledge base with proper error handling"""
        try:
            collection_name = f"user_{user.id}_transcriptions"
            
            # Get Qdrant stats if available
            vector_count = 0
            if self.qdrant_available:
                try:
                    collection_info = self.qdrant_client.get_collection(collection_name)
                    vector_count = collection_info.points_count
                    logger.info(f"Qdrant collection {collection_name} has {vector_count} points")
                except Exception as e:
                    logger.warning(f"Could not get Qdrant stats: {e}")
                    vector_count = 0
            
            # Get database stats with proper SQLAlchemy
            transcription_count = db.query(Transcription).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed"
            ).count()
            
            query_count = db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).count()
            
            # Get total duration
            total_duration = db.query(
                func.sum(Transcription.duration_seconds)
            ).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed"
            ).scalar() or 0
            
            # Count transcriptions with knowledge base storage
            kb_stored_count = db.query(Transcription).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed",
                Transcription.qdrant_point_ids.isnot(None)
            ).count()
            
            logger.info(f"Knowledge base stats for user {user.id}:")
            logger.info(f"  - Total completed transcriptions: {transcription_count}")
            logger.info(f"  - Transcriptions in knowledge base: {kb_stored_count}")
            logger.info(f"  - Vector points in Qdrant: {vector_count}")
            logger.info(f"  - Total queries made: {query_count}")
            
            return {
                "transcription_count": transcription_count,
                "vector_count": vector_count,
                "query_count": query_count,
                "total_duration_hours": round(total_duration / 3600, 2) if total_duration else 0,
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base stats: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                "transcription_count": 0,
                "vector_count": 0,
                "query_count": 0,
                "total_duration_hours": 0,
                "collection_name": collection_name,
                "error": str(e)
            }

    async def get_query_history(
        self, 
        db: Session, 
        user: User, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict]:
        """Get user's query history"""
        try:
            queries = db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).order_by(
                KnowledgeQuery.created_at.desc()
            ).limit(limit).offset(offset).all()
            
            return [
                {
                    "id": str(q.id),
                    "query": q.query,
                    "answer": q.answer,
                    "confidence": q.confidence,
                    "response_time_ms": q.response_time_ms,
                    "created_at": q.created_at.isoformat(),
                    "source_count": q.source_count
                }
                for q in queries
            ]
            
        except Exception as e:
            logger.error(f"Failed to get query history: {e}")
            return []

    async def delete_query_history(self, db: Session, user: User) -> bool:
        """Delete user's query history"""
        try:
            db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).delete()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete query history: {e}")
            db.rollback()
            return False

    async def clear_knowledge_base(self, db: Session, user: User) -> bool:
        """Clear user's entire knowledge base"""
        try:
            collection_name = f"user_{user.id}_transcriptions"
            
            # Delete from Qdrant if available
            if self.qdrant_available:
                try:
                    self.qdrant_client.delete_collection(collection_name)
                    logger.info(f"Deleted Qdrant collection: {collection_name}")
                except Exception as e:
                    logger.warning(f"Qdrant collection deletion failed: {e}")
            
            # Update transcriptions to remove Qdrant references
            transcriptions = db.query(Transcription).filter(
                Transcription.user_id == user.id,
                Transcription.qdrant_point_ids.isnot(None)
            ).all()
            
            for transcription in transcriptions:
                transcription.qdrant_point_ids = None
                transcription.qdrant_collection = None
            
            # Delete query history
            await self.delete_query_history(db, user)
            
            db.commit()
            logger.info(f"Cleared knowledge base for user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            db.rollback()
            return False