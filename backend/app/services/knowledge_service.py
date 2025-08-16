# backend/app/services/knowledge_service.py
import time
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..config import settings
from ..models import KnowledgeQuery, User, Transcription

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
    
    async def query_knowledge_base(
        self, 
        db: Session, 
        user: User, 
        query: str, 
        limit: int = 5
    ) -> Dict:
        """
        Query the user's knowledge base and return contextual answer
        """
        try:
            start_time = time.time()
            collection_name = f"user_{user.id}_transcriptions"
            
            # Check if user has any data
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                if collection_info.points_count == 0:
                    return {
                        "answer": "No transcriptions found in your knowledge base. Please upload and process some audio files first.",
                        "sources": [],
                        "confidence": 0.0,
                        "query_id": ""
                    }
            except Exception as e:
                logger.warning(f"Collection not found: {e}")
                return {
                    "answer": "No knowledge base found. Please upload and process some audio files first.",
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
                score_threshold=0.5  # Lower threshold for better results
            )
            
            if not search_results:
                return {
                    "answer": "I couldn't find relevant information in your transcriptions for this query. Try asking about topics from your uploaded content.",
                    "sources": [],
                    "confidence": 0.0,
                    "query_id": ""
                }
            
            # Build context from search results
            context_parts = []
            source_transcriptions = []
            
            for result in search_results:
                context_parts.append(f"Content: {result.payload['text']}")
                
                # Get source transcription info
                transcription_id = result.payload.get('transcription_id')
                if transcription_id:
                    try:
                        from sqlalchemy import text
                        # Use raw SQL to avoid the func issue
                        query_sql = text("""
                            SELECT id, title, created_at 
                            FROM transcriptions 
                            WHERE id = :transcription_id AND user_id = :user_id
                        """)
                        
                        result_row = db.execute(query_sql, {
                            "transcription_id": transcription_id,
                            "user_id": str(user.id)
                        }).first()
                        
                        if result_row:
                            source_transcriptions.append({
                                "id": str(result_row[0]),
                                "title": result_row[1],
                                "date": result_row[2].strftime("%Y-%m-%d"),
                                "confidence": result.score,
                                "type": result.payload.get('type', 'transcription')
                            })
                            
                    except Exception as e:
                        logger.error(f"Error fetching transcription info: {e}")
                        # Fallback with basic info
                        source_transcriptions.append({
                            "id": transcription_id,
                            "title": "Unknown transcription",
                            "date": "Unknown",
                            "confidence": result.score,
                            "type": result.payload.get('type', 'transcription')
                        })
            
            context = "\n\n".join(context_parts)
            
            # Generate answer using Groq
            answer = await self._generate_contextual_answer(query, context)
            
            # Calculate average confidence
            avg_confidence = sum(r.score for r in search_results) / len(search_results)
            
            # Save query to database
            response_time = int((time.time() - start_time) * 1000)
            
            try:
                knowledge_query = KnowledgeQuery(
                    user_id=user.id,
                    query_text=query,
                    response_text=answer,
                    transcription_ids=[s["id"] for s in source_transcriptions],
                    confidence_score=avg_confidence,
                    response_time_ms=response_time
                )
                db.add(knowledge_query)
                db.commit()
                query_id = str(knowledge_query.id)
            except Exception as e:
                logger.error(f"Failed to save query: {e}")
                query_id = ""
            
            return {
                "answer": answer,
                "sources": source_transcriptions,
                "confidence": avg_confidence,
                "query_id": query_id
            }
            
        except Exception as e:
            logger.error(f"Knowledge base query failed: {e}")
            return {
                "answer": f"I encountered an error while searching your knowledge base: {str(e)}. Please try again or contact support.",
                "sources": [],
                "confidence": 0.0,
                "query_id": ""
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
        """Get statistics about user's knowledge base"""
        try:
            collection_name = f"user_{user.id}_transcriptions"
            
            # Get Qdrant stats
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                vector_count = collection_info.points_count
            except:
                vector_count = 0
            
            # Get database stats
            transcription_count = db.query(Transcription).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed"
            ).count()
            
            query_count = db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).count()
            
            # Get total duration
            total_duration = db.query(
                db.func.sum(Transcription.duration_seconds)
            ).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed"
            ).scalar() or 0
            
            return {
                "transcription_count": transcription_count,
                "vector_count": vector_count,
                "query_count": query_count,
                "total_duration_hours": round(total_duration / 3600, 2),
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base stats: {e}")
            return {
                "transcription_count": 0,
                "vector_count": 0,
                "query_count": 0,
                "total_duration_hours": 0,
                "collection_name": f"user_{user.id}_transcriptions"
            }