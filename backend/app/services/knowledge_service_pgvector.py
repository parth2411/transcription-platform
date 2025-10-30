"""
Knowledge Service - pgvector Implementation
This is the updated knowledge service that uses Supabase pgvector instead of Qdrant.
Replace the existing knowledge_service.py with this after migration.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sentence_transformers import SentenceTransformer
import os
from groq import Groq

from app.models import KnowledgeQuery, Transcription, TranscriptionChunk

class KnowledgeService:
    """
    Knowledge base service using Supabase pgvector for semantic search.
    Replaces Qdrant-based implementation.
    """

    def __init__(self, db: Session):
        self.db = db
        # Use same embedding model as before (384 dimensions)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def query_knowledge_base(
        self,
        user_id: UUID,
        query_text: str,
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Query knowledge base using pgvector similarity search.

        Args:
            user_id: User's UUID
            query_text: Search query
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Dict with answer, sources, and query_id
        """

        # Generate query embedding
        query_embedding = self.model.encode(query_text).tolist()
        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Search using pgvector (cosine similarity)
        # Uses <=> operator for cosine distance (1 - similarity)
        results = self.db.execute(text("""
            SELECT
                tc.id,
                tc.transcription_id,
                tc.text,
                tc.chunk_index,
                t.filename,
                t.created_at,
                1 - (tc.embedding <=> :query_embedding::vector) as similarity
            FROM transcription_chunks tc
            JOIN transcriptions t ON t.id = tc.transcription_id
            WHERE t.user_id = :user_id
              AND tc.embedding IS NOT NULL
              AND 1 - (tc.embedding <=> :query_embedding::vector) > :threshold
            ORDER BY tc.embedding <=> :query_embedding::vector
            LIMIT :limit
        """), {
            "query_embedding": vector_str,
            "user_id": str(user_id),
            "threshold": similarity_threshold,
            "limit": limit
        }).fetchall()

        # Format sources
        sources = []
        for row in results:
            sources.append({
                "chunk_id": str(row[0]),
                "transcription_id": str(row[1]),
                "text": row[2],
                "chunk_index": row[3],
                "filename": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "similarity": float(row[6])
            })

        # Generate answer using Groq
        if sources:
            context_text = "\n\n".join([
                f"From {s['filename']} (chunk {s['chunk_index']}):\n{s['text']}"
                for s in sources
            ])
            answer = await self._generate_answer(query_text, context_text)
            confidence = sources[0]["similarity"]
        else:
            answer = "No relevant information found in your transcriptions."
            confidence = 0.0

        # Save query to database
        query_record = KnowledgeQuery(
            user_id=user_id,
            query_text=query_text,
            response_text=answer,
            transcription_ids=[s["transcription_id"] for s in sources],
            confidence_score=confidence
        )
        self.db.add(query_record)
        self.db.commit()
        self.db.refresh(query_record)

        return {
            "answer": answer,
            "sources": sources,
            "query_id": str(query_record.id),
            "confidence": confidence
        }

    async def store_transcription(
        self,
        transcription_id: UUID,
        text: str,
        user_id: UUID,
        summary: Optional[str] = None
    ) -> int:
        """
        Store transcription with vector embeddings in pgvector.

        Args:
            transcription_id: Transcription UUID
            text: Full transcription text
            user_id: User's UUID
            summary: Optional summary text

        Returns:
            Number of chunks created
        """

        # Split text into chunks
        chunks = self._split_text(text, chunk_size=1000)

        # Generate embeddings and store chunks
        for i, chunk_text in enumerate(chunks):
            # Generate embedding for chunk
            embedding = self.model.encode(chunk_text).tolist()
            vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

            # Insert chunk with embedding
            self.db.execute(text("""
                INSERT INTO transcription_chunks
                (transcription_id, chunk_index, text, embedding)
                VALUES (:transcription_id, :chunk_index, :text, :embedding::vector)
            """), {
                "transcription_id": str(transcription_id),
                "chunk_index": i,
                "text": chunk_text,
                "embedding": vector_str
            })

        # Also store full transcription embedding (optional, for whole-doc search)
        full_embedding = self.model.encode(text[:5000]).tolist()  # Limit to first 5k chars
        full_vector_str = "[" + ",".join(str(v) for v in full_embedding) + "]"

        self.db.execute(text("""
            UPDATE transcriptions
            SET embedding = :embedding::vector
            WHERE id = :transcription_id
        """), {
            "transcription_id": str(transcription_id),
            "embedding": full_vector_str
        })

        self.db.commit()

        return len(chunks)

    async def delete_transcription_vectors(self, transcription_id: UUID) -> bool:
        """
        Delete all vector chunks for a transcription.

        Args:
            transcription_id: Transcription UUID

        Returns:
            True if successful
        """
        try:
            self.db.execute(text("""
                DELETE FROM transcription_chunks
                WHERE transcription_id = :transcription_id
            """), {"transcription_id": str(transcription_id)})

            self.db.execute(text("""
                UPDATE transcriptions
                SET embedding = NULL
                WHERE id = :transcription_id
            """), {"transcription_id": str(transcription_id)})

            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    async def get_knowledge_base_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get statistics about user's knowledge base.

        Args:
            user_id: User's UUID

        Returns:
            Dict with statistics
        """

        # Get transcription and chunk counts
        stats = self.db.execute(text("""
            SELECT
                COUNT(DISTINCT t.id) as transcription_count,
                COUNT(tc.id) as chunk_count,
                AVG(LENGTH(tc.text)) as avg_chunk_length,
                SUM(t.duration_seconds) as total_duration
            FROM transcriptions t
            LEFT JOIN transcription_chunks tc ON tc.transcription_id = t.id
            WHERE t.user_id = :user_id
              AND t.add_to_knowledge_base = true
        """), {"user_id": str(user_id)}).fetchone()

        # Get query count
        query_count = self.db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == user_id
        ).count()

        return {
            "transcription_count": stats[0] or 0,
            "chunk_count": stats[1] or 0,
            "query_count": query_count,
            "avg_chunk_length": int(stats[2]) if stats[2] else 0,
            "total_duration_seconds": int(stats[3]) if stats[3] else 0
        }

    async def get_query_history(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's query history.

        Args:
            user_id: User's UUID
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of query records
        """

        queries = self.db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == user_id
        ).order_by(
            KnowledgeQuery.created_at.desc()
        ).limit(limit).offset(offset).all()

        return [
            {
                "id": str(q.id),
                "query_text": q.query_text,
                "response_text": q.response_text,
                "confidence_score": q.confidence_score,
                "source_count": len(q.transcription_ids) if q.transcription_ids else 0,
                "created_at": q.created_at.isoformat()
            }
            for q in queries
        ]

    async def delete_query_history(self, user_id: UUID) -> int:
        """
        Delete all queries for a user.

        Args:
            user_id: User's UUID

        Returns:
            Number of queries deleted
        """

        count = self.db.query(KnowledgeQuery).filter(
            KnowledgeQuery.user_id == user_id
        ).delete()
        self.db.commit()

        return count

    async def clear_knowledge_base(self, user_id: UUID) -> bool:
        """
        Clear all vectors and queries for a user.

        Args:
            user_id: User's UUID

        Returns:
            True if successful
        """

        try:
            # Delete all chunks for user's transcriptions
            self.db.execute(text("""
                DELETE FROM transcription_chunks
                WHERE transcription_id IN (
                    SELECT id FROM transcriptions WHERE user_id = :user_id
                )
            """), {"user_id": str(user_id)})

            # Clear embeddings from transcriptions
            self.db.execute(text("""
                UPDATE transcriptions
                SET embedding = NULL
                WHERE user_id = :user_id
            """), {"user_id": str(user_id)})

            # Delete query history
            self.db.query(KnowledgeQuery).filter(
                KnowledgeQuery.user_id == user_id
            ).delete()

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            raise e

    async def search_similar_transcriptions(
        self,
        user_id: UUID,
        transcription_id: UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar transcriptions to a given one.

        Args:
            user_id: User's UUID
            transcription_id: Reference transcription UUID
            limit: Number of results

        Returns:
            List of similar transcriptions
        """

        # Get embedding of reference transcription
        result = self.db.execute(text("""
            SELECT embedding FROM transcriptions
            WHERE id = :transcription_id AND user_id = :user_id
        """), {
            "transcription_id": str(transcription_id),
            "user_id": str(user_id)
        }).fetchone()

        if not result or not result[0]:
            return []

        # Find similar transcriptions
        results = self.db.execute(text("""
            SELECT
                t.id,
                t.filename,
                t.transcription_text,
                t.duration_seconds,
                t.created_at,
                1 - (t.embedding <=> (
                    SELECT embedding FROM transcriptions WHERE id = :transcription_id
                )) as similarity
            FROM transcriptions t
            WHERE t.user_id = :user_id
              AND t.id != :transcription_id
              AND t.embedding IS NOT NULL
            ORDER BY t.embedding <=> (
                SELECT embedding FROM transcriptions WHERE id = :transcription_id
            )
            LIMIT :limit
        """), {
            "transcription_id": str(transcription_id),
            "user_id": str(user_id),
            "limit": limit
        }).fetchall()

        return [
            {
                "id": str(row[0]),
                "filename": row[1],
                "preview": row[2][:200] if row[2] else "",
                "duration_seconds": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "similarity": float(row[5])
            }
            for row in results
        ]

    # Private helper methods

    def _split_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """
        Split text into chunks for embedding.

        Args:
            text: Text to split
            chunk_size: Maximum characters per chunk

        Returns:
            List of text chunks
        """

        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    async def _generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using Groq LLM.

        Args:
            query: User's question
            context: Retrieved context from vector search

        Returns:
            Generated answer
        """

        prompt = f"""You are a helpful assistant analyzing transcription data.

Context from transcriptions:
{context}

User question: {query}

Please provide a comprehensive answer based on the context above. If the context doesn't contain enough information, say so clearly."""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided transcription context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error generating answer: {str(e)}"
