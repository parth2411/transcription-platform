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
        """Query the user's knowledge base using scroll method"""
        
        if not self.qdrant_available:
            return {
                "answer": "Knowledge base service is currently unavailable.",
                "sources": [],
                "confidence": 0.0,
                "query_id": ""
            }
        
        if not self.embedder_available:
            return {
                "answer": "Text embedding service is currently unavailable.",
                "sources": [],
                "confidence": 0.0,
                "query_id": ""
            }
        
        try:
            start_time = time.time()
            collection_name = f"user_{user.id}_transcriptions"
            
            # Check if collection exists and has data using scroll method
            try:
                collections = self.qdrant_client.get_collections()
                collection_names = [c.name for c in collections.collections]
                
                if collection_name not in collection_names:
                    return {
                        "answer": "No knowledge base found. Please upload and process some audio files with 'Add to Knowledge Base' enabled.",
                        "sources": [],
                        "confidence": 0.0,
                        "query_id": ""
                    }
                
                # Use scroll to check if collection has data
                test_scroll = self.qdrant_client.scroll(
                    collection_name=collection_name,
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )
                
                if len(test_scroll[0]) == 0:
                    return {
                        "answer": "No transcriptions found in your knowledge base. Please upload and process some audio files with 'Add to Knowledge Base' enabled.",
                        "sources": [],
                        "confidence": 0.0,
                        "query_id": ""
                    }
                
                logger.info(f"Collection {collection_name} has data, proceeding with search")
                
            except Exception as e:
                logger.warning(f"Collection check failed: {e}")
                return {
                    "answer": "Error accessing knowledge base. Please try again later.",
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
                score_threshold=0.3
            )
            
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
                    "answer": "Found relevant transcriptions but could not extract content.",
                    "sources": sources,
                    "confidence": 0.0,
                    "query_id": ""
                }
            
            # Generate answer using Groq
            if self.groq_available:
                context = "\\n\\n".join(context_parts)
                
                prompt = f"""
                Based on the following transcriptions from the user's knowledge base, answer their question accurately and helpfully.
                
                User's Question: {query}
                
                Relevant Transcriptions:
                {context}
                
                Please provide a comprehensive answer based on the content above.
                """
                
                try:
                    response = self.groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    
                    answer = response.choices[0].message.content
                    confidence = min(sum(s["confidence"] for s in sources) / len(sources), 1.0)
                    
                except Exception as e:
                    logger.error(f"Groq API error: {e}")
                    answer = f"Found {len(sources)} relevant transcription(s) but could not generate a comprehensive answer."
                    confidence = 0.5
            else:
                answer = f"Found {len(sources)} relevant transcription(s). AI summarization is currently unavailable."
                confidence = 0.5
            
            # Store query in database
            query_id = str(uuid.uuid4())
            query_record = KnowledgeQuery(
                id=query_id,
                user_id=user.id,
                query_text=query,
                response_text=answer,
                confidence_score=confidence,
                response_time_ms=int((time.time() - start_time) * 1000),
            )
            db.add(query_record)
            db.commit()
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "query_id": query_id
            }
            
        except Exception as e:
            logger.error(f"Knowledge base query failed: {e}")
            return {
                "answer": "An error occurred while searching your knowledge base. Please try again later.",
                "sources": [],
                "confidence": 0.0,
                "query_id": ""
            }

    async def get_knowledge_base_stats(self, db: Session, user: User) -> Dict:
        """Get statistics about user's knowledge base using scroll method"""
        try:
            collection_name = f"user_{user.id}_transcriptions"
            
            # Get Qdrant stats using scroll method (avoids Pydantic validation issues)
            vector_count = 0
            if self.qdrant_available and self.qdrant_client:
                try:
                    # First check if collection exists by listing collections
                    collections = self.qdrant_client.get_collections()
                    collection_names = [c.name for c in collections.collections]
                    
                    if collection_name in collection_names:
                        # Use scroll to count points (avoids get_collection Pydantic issues)
                        logger.info(f"Counting points in collection: {collection_name}")
                        scroll_result = self.qdrant_client.scroll(
                            collection_name=collection_name,
                            limit=10000,  # Large limit to get all points
                            with_payload=False,
                            with_vectors=False
                        )
                        vector_count = len(scroll_result[0])
                        logger.info(f"✅ Found {vector_count} vectors in {collection_name}")
                    else:
                        logger.info(f"ℹ️  Collection {collection_name} does not exist yet")
                        vector_count = 0
                        
                except Exception as e:
                    logger.warning(f"Could not get Qdrant stats: {e}")
                    vector_count = 0
            else:
                logger.info("Qdrant client not available")
                vector_count = 0
            
            # Get database stats
            transcription_count = db.query(Transcription).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed"
            ).count()
            
            query_count = db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user.id
            ).count()
            
            total_duration = db.query(
                func.sum(Transcription.duration_seconds)
            ).filter(
                Transcription.user_id == user.id,
                Transcription.status == "completed"
            ).scalar() or 0
            
            logger.info(f"Knowledge base stats for user {user.id}:")
            logger.info(f"  - Total completed transcriptions: {transcription_count}")
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
            return {
                "transcription_count": 0,
                "vector_count": 0,
                "query_count": 0,
                "total_duration_hours": 0,
                "collection_name": f"user_{user.id}_transcriptions",
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
                    "query": q.query_text,
                    "answer": q.response_text,
                    "confidence": q.confidence_score,
                    "response_time_ms": q.response_time_ms,
                    "created_at": q.created_at.isoformat(),
                    "source_count": 0  # Default value since this field doesn't exist in model
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
    # Add this method to your existing KnowledgeService class
    # backend/app/services/knowledge_service.py

    async def store_transcription(
        self,
        transcription_id: str,
        title: str,
        content: str,
        summary: str = None,
        user_id: str = None
    ) -> List[str]:
        """
        Store transcription content in the knowledge base
        """
        try:
            if not self.qdrant_available or not self.embedder_available:
                logger.warning("Qdrant or embedder not available, skipping storage")
                return []
            
            collection_name = f"user_{user_id}_transcriptions"
            point_ids = []
            
            # Ensure collection exists
            await self._ensure_collection_exists(collection_name)
            
            # Split content into chunks for better retrieval
            content_chunks = self._split_text_into_chunks(content, max_chunk_size=1000)
            
            for i, chunk in enumerate(content_chunks):
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue
                    
                # Generate embedding
                embedding = self.embedder.encode(chunk)
                
                # Create point
                point_id = f"{transcription_id}_chunk_{i}"
                point_ids.append(point_id)
                
                # Create metadata
                metadata = {
                    "transcription_id": transcription_id,
                    "title": title,
                    "chunk_index": i,
                    "content_type": "transcription_chunk",
                    "text_preview": chunk[:200],
                    "full_text": chunk,
                    "created_at": datetime.utcnow().isoformat(),
                    "user_id": user_id
                }
                
                # Store in Qdrant
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=[{
                        "id": point_id,
                        "vector": embedding.tolist(),
                        "payload": metadata
                    }]
                )
            
            # Store summary if provided
            if summary and summary.strip():
                summary_embedding = self.embedder.encode(summary)
                summary_point_id = f"{transcription_id}_summary"
                point_ids.append(summary_point_id)
                
                summary_metadata = {
                    "transcription_id": transcription_id,
                    "title": title,
                    "content_type": "summary",
                    "text_preview": summary[:200],
                    "full_text": summary,
                    "created_at": datetime.utcnow().isoformat(),
                    "user_id": user_id
                }
                
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=[{
                        "id": summary_point_id,
                        "vector": summary_embedding.tolist(),
                        "payload": summary_metadata
                    }]
                )
            
            logger.info(f"Stored transcription {transcription_id} as {len(point_ids)} points")
            return point_ids
            
        except Exception as e:
            logger.error(f"Failed to store transcription {transcription_id}: {e}")
            return []

    def _split_text_into_chunks(self, text: str, max_chunk_size: int = 1000) -> List[str]:
        """
        Split text into chunks for better embedding and retrieval
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence + '. ') <= max_chunk_size:
                current_chunk += sentence + '. '
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '. '
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    async def _ensure_collection_exists(self, collection_name: str):
        """
        Ensure the collection exists, create if it doesn't
        """
        try:
            self.qdrant_client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist, create it
            from qdrant_client.models import Distance, VectorParams
            
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Created collection: {collection_name}")