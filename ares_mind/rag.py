"""
RAG Store - Retrieval-Augmented Generation using ChromaDB.

Provides semantic search over conversation history to inject relevant
past conversations into LLM context.

Requires Ollama with an embedding model (e.g., nomic-embed-text) for embeddings.
Pull the model with: ollama pull nomic-embed-text
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
_chromadb = None


def _get_chromadb():
    """Lazy load chromadb."""
    global _chromadb
    if _chromadb is None:
        import chromadb
        _chromadb = chromadb
    return _chromadb


class RAGStore:
    """
    Manages conversation embeddings in ChromaDB for semantic retrieval.
    
    Uses Ollama's /api/embeddings endpoint for generating embeddings.
    Requires the embedding model to be pulled: ollama pull nomic-embed-text
    
    Usage:
        store = RAGStore()
        store.index_message(message_id, content, metadata)
        results = store.search(query, n_results=5)
    """
    
    COLLECTION_NAME = "ares_conversations"
    EMBEDDING_MODEL = "nomic-embed-text"  # Ollama embedding model
    EMBEDDING_DIMENSIONS = 768  # nomic-embed-text produces 768-dim vectors
    
    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize RAG store with ChromaDB.
        
        Args:
            persist_path: Path for ChromaDB persistence. If None, uses config default.
        """
        from ares_core.config import CHROMADB_PATH, OLLAMA_BASE_URL
        
        self.persist_path = persist_path or CHROMADB_PATH
        self.ollama_base_url = OLLAMA_BASE_URL
        self._client = None
        self._collection = None
        self._use_ollama_embeddings = None  # Will be determined on first use
        self._http_client = None
    
    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client for Ollama."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client
    
    def _get_client(self):
        """Get or create ChromaDB client."""
        if self._client is None:
            chromadb = _get_chromadb()
            self._client = chromadb.PersistentClient(path=self.persist_path)
            logger.info(f"Initialized ChromaDB at {self.persist_path}")
        return self._client
    
    def _get_collection(self):
        """Get or create the conversations collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "ARES conversation history for RAG"}
            )
            logger.info(f"Using collection '{self.COLLECTION_NAME}' with {self._collection.count()} documents")
        return self._collection
    
    def _check_ollama_embeddings(self) -> bool:
        """Check if Ollama embeddings are available."""
        if self._use_ollama_embeddings is not None:
            return self._use_ollama_embeddings
        
        try:
            client = self._get_http_client()
            # Try to get embeddings for a test string
            response = client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.EMBEDDING_MODEL,
                    "prompt": "test"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                if "embedding" in data and len(data["embedding"]) > 0:
                    self._use_ollama_embeddings = True
                    logger.info(f"Using Ollama embeddings with model '{self.EMBEDDING_MODEL}'")
                    return True
            
            # Model might not be pulled
            if response.status_code == 404:
                logger.error(
                    f"Embedding model '{self.EMBEDDING_MODEL}' not found. "
                    f"Pull it with: ollama pull {self.EMBEDDING_MODEL}"
                )
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.ollama_base_url}")
        except Exception as e:
            logger.error(f"Ollama embeddings check failed: {e}")
        
        self._use_ollama_embeddings = False
        return False
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text using Ollama.
        
        Raises:
            RuntimeError: If Ollama embeddings are not available
        """
        if not self._check_ollama_embeddings():
            raise RuntimeError(
                f"Ollama embeddings not available. "
                f"Ensure Ollama is running at {self.ollama_base_url} and pull the model: "
                f"ollama pull {self.EMBEDDING_MODEL}"
            )
        
        try:
            client = self._get_http_client()
            response = client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.EMBEDDING_MODEL,
                    "prompt": text
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception as e:
            raise RuntimeError(f"Ollama embedding failed: {e}")
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts using Ollama."""
        # Ollama doesn't have a native batch endpoint, so we process sequentially
        return [self._get_embedding(text) for text in texts]
    
    def index_message(
        self,
        message_id: str,
        content: str,
        session_id: str,
        role: str,
        user_id: str = "default",
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Index a conversation message for retrieval.
        
        Args:
            message_id: Unique ID for the message
            content: Message text content
            session_id: Chat session ID
            role: Message role (user/assistant)
            user_id: User identifier
            timestamp: Message timestamp
            
        Returns:
            True if indexed successfully
        """
        if not content or not content.strip():
            return False
        
        try:
            collection = self._get_collection()
            
            # Prepare metadata
            metadata = {
                "session_id": session_id,
                "role": role,
                "user_id": user_id,
                "timestamp": timestamp.isoformat() if timestamp else datetime.now().isoformat(),
            }
            
            # Get embedding
            embedding = self._get_embedding(content)
            
            # Upsert to collection
            collection.upsert(
                ids=[message_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata]
            )
            
            logger.debug(f"Indexed message {message_id} ({role})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index message {message_id}: {e}")
            return False
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        user_id: Optional[str] = None,
        exclude_session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant past conversations.
        
        Args:
            query: Search query text
            n_results: Maximum number of results
            user_id: Filter by user ID
            exclude_session_id: Exclude messages from this session (current conversation)
            
        Returns:
            List of results with content, metadata, and distance
        """
        if not query or not query.strip():
            return []
        
        try:
            collection = self._get_collection()
            
            if collection.count() == 0:
                return []
            
            # Build where filter
            where_filter = None
            if user_id:
                where_filter = {"user_id": user_id}
            
            # Get query embedding
            query_embedding = self._get_embedding(query)
            
            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results * 2, 20),  # Get extra to filter
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            output = []
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                
                # Skip messages from excluded session
                if exclude_session_id and metadata.get("session_id") == exclude_session_id:
                    continue
                
                output.append({
                    "id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": metadata,
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
                
                if len(output) >= n_results:
                    break
            
            return output
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
    
    def reindex_all(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Reindex all conversation messages from the database.
        
        Args:
            batch_size: Number of messages to process at once
            
        Returns:
            Stats dict with counts
        """
        try:
            # Import Django models
            from api.models import ConversationMessage
            
            collection = self._get_collection()
            
            # Clear existing collection
            try:
                client = self._get_client()
                client.delete_collection(self.COLLECTION_NAME)
                self._collection = None
                collection = self._get_collection()
            except Exception:
                pass
            
            # Get all messages
            messages = ConversationMessage.objects.select_related('session').order_by('created_at')
            total = messages.count()
            indexed = 0
            failed = 0
            
            logger.info(f"Reindexing {total} messages...")
            
            # Process in batches
            batch_ids = []
            batch_texts = []
            batch_metadatas = []
            
            for msg in messages.iterator():
                if not msg.message or not msg.message.strip():
                    continue
                
                msg_id = f"msg_{msg.id}"
                batch_ids.append(msg_id)
                batch_texts.append(msg.message)
                batch_metadatas.append({
                    "session_id": msg.session.session_id,
                    "role": msg.role,
                    "user_id": "default",  # Could be enhanced with user tracking
                    "timestamp": msg.created_at.isoformat(),
                })
                
                if len(batch_ids) >= batch_size:
                    try:
                        embeddings = self._get_embeddings_batch(batch_texts)
                        collection.upsert(
                            ids=batch_ids,
                            embeddings=embeddings,
                            documents=batch_texts,
                            metadatas=batch_metadatas
                        )
                        indexed += len(batch_ids)
                        logger.info(f"Indexed {indexed}/{total} messages")
                    except Exception as e:
                        logger.error(f"Batch indexing failed: {e}")
                        failed += len(batch_ids)
                    
                    batch_ids = []
                    batch_texts = []
                    batch_metadatas = []
            
            # Process remaining
            if batch_ids:
                try:
                    embeddings = self._get_embeddings_batch(batch_texts)
                    collection.upsert(
                        ids=batch_ids,
                        embeddings=embeddings,
                        documents=batch_texts,
                        metadatas=batch_metadatas
                    )
                    indexed += len(batch_ids)
                except Exception as e:
                    logger.error(f"Final batch indexing failed: {e}")
                    failed += len(batch_ids)
            
            logger.info(f"Reindex complete: {indexed} indexed, {failed} failed")
            
            return {
                "total": total,
                "indexed": indexed,
                "failed": failed,
            }
            
        except Exception as e:
            logger.error(f"Reindex failed: {e}")
            return {"error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG store statistics."""
        try:
            collection = self._get_collection()
            
            return {
                "collection_name": self.COLLECTION_NAME,
                "document_count": collection.count(),
                "persist_path": self.persist_path,
                "embedding_model": self.EMBEDDING_MODEL,
                "embedding_available": self._use_ollama_embeddings if self._use_ollama_embeddings is not None else "not checked",
                "ollama_url": self.ollama_base_url,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message from the index."""
        try:
            collection = self._get_collection()
            collection.delete(ids=[message_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all indexed documents."""
        try:
            client = self._get_client()
            client.delete_collection(self.COLLECTION_NAME)
            self._collection = None
            logger.info("RAG store cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear RAG store: {e}")
            return False


# Singleton instance
rag_store = RAGStore()

