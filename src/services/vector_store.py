"""
Vector Store Service for Semantic Code Search.

Uses ChromaDB for embedding-based code search and RAG retrieval.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Lazy imports for optional dependencies
_chromadb = None
_embeddings = None


def _get_chromadb():
    """Lazily import ChromaDB."""
    global _chromadb
    if _chromadb is None:
        try:
            import chromadb
            _chromadb = chromadb
            logger.info("ChromaDB imported successfully")
        except ImportError:
            logger.warning("ChromaDB not installed. Semantic search disabled.")
    return _chromadb


class VectorStore:
    """
    Vector store for semantic code search using ChromaDB.
    
    Provides:
    - Code embedding and indexing
    - Semantic similarity search
    - Context retrieval for RAG
    """
    
    def __init__(
        self,
        collection_name: str = "code_repository",
        persist_directory: Optional[str] = None
    ):
        """
        Initialize vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Optional directory for persistence
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self._initialized = False
        
        logger.info(f"VectorStore initialized with collection: {collection_name}")
    
    def initialize(self) -> bool:
        """
        Initialize ChromaDB client and collection.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
        
        chromadb = _get_chromadb()
        if chromadb is None:
            return False
        
        try:
            if self.persist_directory:
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory
                )
                logger.info(f"Using persistent ChromaDB at: {self.persist_directory}")
            else:
                self.client = chromadb.Client()
                logger.info("Using in-memory ChromaDB")
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Code repository for semantic search"}
            )
            
            self._initialized = True
            logger.info(f"ChromaDB collection ready: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}", exc_info=True)
            return False
    
    def add_code(
        self,
        file_path: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add code file to the vector store.
        
        Args:
            file_path: Path to the code file
            content: File contents
            metadata: Optional additional metadata
            
        Returns:
            True if successful
        """
        if not self.initialize():
            return False
        
        try:
            # Split content into chunks for better retrieval
            chunks = self._chunk_code(content)
            
            ids = []
            documents = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_path}:chunk_{i}"
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append({
                    "file_path": file_path,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "indexed_at": datetime.now().isoformat(),
                    **(metadata or {})
                })
            
            # Upsert to handle updates
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Indexed {len(chunks)} chunks from: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add code to vector store: {e}", exc_info=True)
            return False
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        file_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar code.
        
        Args:
            query: Search query
            n_results: Number of results to return
            file_filter: Optional list of file patterns to filter
            
        Returns:
            List of search results with metadata
        """
        if not self.initialize():
            return []
        
        try:
            where_filter = None
            if file_filter:
                where_filter = {
                    "$or": [
                        {"file_path": {"$contains": f}}
                        for f in file_filter
                    ]
                }
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            # Format results
            formatted = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results.get("distances") else None
                    })
            
            logger.info(f"Search '{query[:50]}...' returned {len(formatted)} results")
            return formatted
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []
    
    def delete_file(self, file_path: str) -> bool:
        """
        Remove a file from the vector store.
        
        Args:
            file_path: Path of file to remove
            
        Returns:
            True if successful
        """
        if not self.initialize():
            return False
        
        try:
            # Delete all chunks for this file
            self.collection.delete(
                where={"file_path": file_path}
            )
            logger.info(f"Removed from index: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete from vector store: {e}", exc_info=True)
            return False
    
    def _chunk_code(
        self,
        content: str,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[str]:
        """
        Split code into overlapping chunks.
        
        Args:
            content: Code content to split
            chunk_size: Maximum chunk size
            overlap: Overlap between chunks
            
        Returns:
            List of code chunks
        """
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at a newline
            if end < len(content):
                newline_pos = content.rfind('\n', start, end)
                if newline_pos > start:
                    end = newline_pos + 1
            
            chunks.append(content[start:end])
            start = end - overlap
        
        return chunks
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.
        
        Returns:
            Dictionary with stats
        """
        if not self.initialize():
            return {"status": "not_initialized"}
        
        try:
            count = self.collection.count()
            return {
                "status": "initialized",
                "collection": self.collection_name,
                "document_count": count,
                "persistent": self.persist_directory is not None
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(
            collection_name="ai_code_reviewer",
            persist_directory=os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                ".chroma"
            )
        )
    return _vector_store
