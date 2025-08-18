# backend/app/services/knowledge_service.py
import time
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from sqlalchemy import func
import uuid
import os

from ..config import settings
from ..models import KnowledgeQuery, User, Transcription
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        # self.qdrant_client = QdrantClient(
        #     url=settings.QDRANT_URL,
        #     api_key=settings.QDRANT_API_KEY
        # )
        # self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        # self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        try:
            self.qdrant_client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=60,
                prefer_grpc=False  # This fixes the pydantic errors
            )
            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"✅ Qdrant connected: {len(collections.collections)} collections")
        except Exception as e:
            logger.error(f"❌ Qdrant failed: {e}")
            self.qdrant_client = None
    
    async def query_knowledge_base(
        self, 
        db: Session, 
        user: User, 
        query: str, 
        limit: int = 5
    ) -> Dict:
        """Query the user's knowledge base and return contextual answer"""
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
            except Exception as e:
                logger.warning(f"Collection not found or error: {e}")
                return {
                    "answer": "No knowledge base found. Please upload and process some audio files with 'Add to Knowledge Base' enabled.",
                    "sources": [],
                    "confidence": 0.0,
                    "query_id": ""
                }
            
            # Create query vector
            query_vector = self.embedder.encode(query).tolist()
            
            # Search similar content
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.3  # Lower threshold for better results
            )
            
            if not search_results:
                return {
                    "answer": "I couldn't find relevant information in your transcriptions for this query. Try asking about topics from your uploaded content or check if your transcriptions are being stored in the knowledge base.",
                    "sources": [],
                    "confidence": 0.0,
                    "query_id": ""
                }
            
            # Prepare context for LLM
            context_parts = []
            sources = []
            
            for result in search_results:
                payload = result.payload
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
            context = "\n\n".join(context_parts)
            
            prompt = f"""
            Based on the following transcriptions from the user's knowledge base, answer their question accurately and helpfully.
            
            User's Question: {query}
            
            Relevant Transcriptions:
            {context}
            
            Please provide a comprehensive answer based on the content above. If the transcriptions don't contain enough information to fully answer the question, say so and suggest what additional information might be needed.
            """
            
            response = self.groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            query_id = str(uuid.uuid4())
            
            # Save query to history
            try:
                knowledge_query = KnowledgeQuery(
                    user_id=user.id,
                    query_text=query,
                    response_text=answer,
                    confidence_score=max([s["confidence"] for s in sources]) if sources else 0.0,
                    sources_count=len(sources),
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                db.add(knowledge_query)
                db.commit()
                query_id = str(knowledge_query.id)
            except Exception as save_error:
                logger.warning(f"Could not save query to history: {save_error}")
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": max([s["confidence"] for s in sources]) if sources else 0.0,
                "query_id": query_id,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
            
        except Exception as e:
            logger.error(f"Knowledge base query failed: {e}")
            return {
                "answer": f"Sorry, there was an error processing your query: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "query_id": "",
                "error": str(e)
            }
        
    async def _generate_contextual_answer(self, query: str, context: str) -> str:
        """Generate answer using Groq with context"""
        try:
            prompt = f"""
Based on the following context from the user's transcriptions, answer their question accurately and comprehensively.

Question: {query}

Context:
{context}

Instructions:
- Provide a clear, direct answer based on the context
- If the context doesn't contain enough information, say so
- Use specific details and quotes from the transcriptions when relevant
- Organize your response with clear structure if dealing with multiple points
- Be conversational but informative

Answer:"""
            
            response = self.groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "I apologize, but I encountered an error while generating the answer. Please try again."
    
    async def get_query_history(
        self, 
        db: Session, 
        user: User, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict]:
        """Get user's query history"""
        try:
            queries = db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).order_by(
                KnowledgeQuery.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            return [
                {
                    "id": str(q.id),
                    "query": q.query_text,
                    "answer": q.response_text,
                    "confidence": q.confidence_score,
                    "response_time_ms": q.response_time_ms,
                    "created_at": q.created_at.isoformat(),
                    "source_count": len(q.transcription_ids) if q.transcription_ids else 0
                }
                for q in queries
            ]
            
        except Exception as e:
            logger.error(f"Failed to get query history: {e}")
            return []
    
    async def delete_query_history(self, db: Session, user: User) -> bool:
        """Delete all query history for user"""
        try:
            db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).delete()
            db.commit()
            
            logger.info(f"Deleted query history for user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete query history: {e}")
            db.rollback()
            return False
    
    async def clear_knowledge_base(self, db: Session, user: User) -> bool:
        """Clear user's entire knowledge base"""
        try:
            collection_name = f"user_{user.id}_transcriptions"
            
            # Delete from Qdrant
            try:
                # Delete entire collection
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
    
    async def get_knowledge_base_stats(self, db: Session, user: User) -> Dict:
        """Get statistics about user's knowledge base with proper SQLAlchemy"""
        try:
            collection_name = f"user_{user.id}_transcriptions"
            
            # Get Qdrant stats
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                vector_count = collection_info.points_count
                logger.info(f"Qdrant collection {collection_name} has {vector_count} points")
            except Exception as e:
                logger.warning(f"Could not get Qdrant stats: {e}")
                vector_count = 0
            
            # Get database stats - Fixed SQLAlchemy usage
            transcription_count = db.query(Transcription).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed"
            ).count()
            
            query_count = db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).count()
            
            # Get total duration - Fixed func usage
            total_duration = db.query(
                func.sum(Transcription.duration_seconds)  # ✅ Use func.sum instead of db.func.sum
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
                "kb_stored_count": kb_stored_count,
                "vector_count": vector_count,
                "query_count": query_count,
                "total_duration_hours": round(total_duration / 3600, 2) if total_duration else 0,
                "collection_name": collection_name,
                "storage_rate": round((kb_stored_count / transcription_count * 100), 1) if transcription_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base stats: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                "transcription_count": 0,
                "kb_stored_count": 0,
                "vector_count": 0,
                "query_count": 0,
                "total_duration_hours": 0,
                "collection_name": collection_name,
                "storage_rate": 0,
                "error": str(e)
            }
