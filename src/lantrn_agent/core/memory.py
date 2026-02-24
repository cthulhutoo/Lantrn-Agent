"""Memory system for Lantrn Agent Builder.

Implements persistent storage with SQLite for structured data
and ChromaDB for vector embeddings (semantic search).
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings


@dataclass
class MemoryEntry:
    """A memory entry with metadata."""
    id: str
    key: str
    value: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class ConversationEntry:
    """A conversation entry."""
    id: str
    run_id: str
    messages: list[dict[str, Any]]
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class TraceEntry:
    """A trace entry for agent actions."""
    id: str
    run_id: str
    action: str
    details: dict[str, Any]
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class MemoryManager:
    """Manages persistent memory with SQLite and ChromaDB backends.
    
    SQLite stores structured data:
    - conversations: run_id, messages, timestamps
    - memories: key-value pairs with metadata
    - traces: agent action traces
    
    ChromaDB stores vector embeddings for semantic search.
    """
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        vector_db_path: Optional[Path] = None,
        embedding_function: str = "default",
    ):
        """Initialize the memory manager.
        
        Args:
            db_path: Path to SQLite database file
            vector_db_path: Path to ChromaDB storage directory
            embedding_function: ChromaDB embedding function name
        """
        self.db_path = Path(db_path) if db_path else Path("./lantrn.db")
        self.vector_db_path = Path(vector_db_path) if vector_db_path else Path("./chroma_db")
        self.embedding_function = embedding_function
        
        # Ensure parent directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite
        self._init_sqlite()
        
        # Initialize ChromaDB
        self._init_chromadb()
    
    def _init_sqlite(self) -> None:
        """Initialize SQLite database with schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL UNIQUE,
                    messages TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    metadata TEXT,
                    embedding_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Traces table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_run_id 
                ON conversations(run_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_key 
                ON memories(key)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_run_id 
                ON traces(run_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_timestamp 
                ON traces(timestamp)
            """)
            
            conn.commit()
    
    def _init_chromadb(self) -> None:
        """Initialize ChromaDB client and collections."""
        # Use persistent client for offline operation
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.vector_db_path),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        
        # Get or create collections
        self.memories_collection = self.chroma_client.get_or_create_collection(
            name="memories",
            metadata={"description": "Agent memories for semantic search"}
        )
        
        self.conversations_collection = self.chroma_client.get_or_create_collection(
            name="conversations",
            metadata={"description": "Conversation embeddings for semantic search"}
        )
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ==================== Memory Operations ====================
    
    def save_memory(
        self,
        key: str,
        value: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Save a memory entry with optional metadata.
        
        Args:
            key: Unique identifier for the memory
            value: The memory content (text)
            metadata: Optional metadata dict
            
        Returns:
            The memory ID
        """
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        metadata = metadata or {}
        
        # Check if key exists
        existing = self.load_memory(key)
        if existing:
            # Update existing memory
            memory_id = existing["id"]
            now = datetime.utcnow().isoformat()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE memories 
                    SET value = ?, metadata = ?, updated_at = ?
                    WHERE key = ?
                """, (value, json.dumps(metadata), now, key))
                conn.commit()
            
            # Update embedding in ChromaDB
            if existing.get("embedding_id"):
                self.memories_collection.delete(ids=[existing["embedding_id"]])
            
            embedding_id = str(uuid.uuid4())
            self.memories_collection.add(
                ids=[embedding_id],
                documents=[value],
                metadatas=[{"key": key, "memory_id": memory_id, **metadata}],
            )
            
            # Update embedding_id in SQLite
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE memories SET embedding_id = ? WHERE id = ?",
                    (embedding_id, memory_id)
                )
                conn.commit()
            
            return memory_id
        
        # Create new memory
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories (id, key, value, metadata, embedding_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (memory_id, key, value, json.dumps(metadata), None, now, now))
            conn.commit()
        
        # Add to ChromaDB for semantic search
        embedding_id = str(uuid.uuid4())
        self.memories_collection.add(
            ids=[embedding_id],
            documents=[value],
            metadatas=[{"key": key, "memory_id": memory_id, **metadata}],
        )
        
        # Update embedding_id in SQLite
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE memories SET embedding_id = ? WHERE id = ?",
                (embedding_id, memory_id)
            )
            conn.commit()
        
        return memory_id
    
    def load_memory(self, key: str) -> Optional[dict[str, Any]]:
        """Load a memory entry by key.
        
        Args:
            key: The memory key
            
        Returns:
            Memory dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM memories WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "key": row["key"],
                    "value": row["value"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "embedding_id": row["embedding_id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
        return None
    
    def search_memories(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Search memories using semantic similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            metadata_filter: Optional metadata filters for ChromaDB
            
        Returns:
            List of matching memory entries with similarity scores
        """
        # Build where clause for ChromaDB
        where = None
        if metadata_filter:
            where = metadata_filter
        
        # Search in ChromaDB
        results = self.memories_collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        memories = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                
                # Get full memory from SQLite
                memory_key = metadata.get("key")
                if memory_key:
                    full_memory = self.load_memory(memory_key)
                    if full_memory:
                        full_memory["similarity_score"] = 1 - distance
                        memories.append(full_memory)
        
        return memories
    
    def delete_memory(self, key: str) -> bool:
        """Delete a memory entry by key.
        
        Args:
            key: The memory key
            
        Returns:
            True if deleted, False if not found
        """
        # Get memory to find embedding_id
        memory = self.load_memory(key)
        if not memory:
            return False
        
        # Delete from ChromaDB
        if memory.get("embedding_id"):
            try:
                self.memories_collection.delete(ids=[memory["embedding_id"]])
            except Exception:
                pass  # Continue even if ChromaDB delete fails
        
        # Delete from SQLite
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
        
        return True
    
    def list_memories(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List all memories with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of memory entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "key": row["key"],
                    "value": row["value"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]
    
    # ==================== Conversation Operations ====================
    
    def save_conversation(
        self,
        run_id: str,
        messages: list[dict[str, Any]],
    ) -> str:
        """Save a conversation for a run.
        
        Args:
            run_id: The run identifier
            messages: List of message dicts
            
        Returns:
            The conversation ID
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Check if conversation exists for this run_id
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, messages FROM conversations WHERE run_id = ?",
                (run_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing conversation
                conversation_id = existing["id"]
                cursor.execute("""
                    UPDATE conversations 
                    SET messages = ?, updated_at = ?
                    WHERE run_id = ?
                """, (json.dumps(messages), now, run_id))
                conn.commit()
                return conversation_id
        
        # Create new conversation
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (id, run_id, messages, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, run_id, json.dumps(messages), now, now))
            conn.commit()
        
        # Add conversation summary to ChromaDB for semantic search
        # Combine all message content for embedding
        conversation_text = "\n".join([
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
        ])
        
        self.conversations_collection.upsert(
            ids=[conversation_id],
            documents=[conversation_text],
            metadatas=[{"run_id": run_id}],
        )
        
        return conversation_id
    
    def get_conversation(self, run_id: str) -> list[dict[str, Any]]:
        """Get conversation messages for a run.
        
        Args:
            run_id: The run identifier
            
        Returns:
            List of message dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT messages FROM conversations WHERE run_id = ?",
                (run_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return json.loads(row["messages"])
        return []
    
    def list_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List all conversations with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of conversation entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "messages": json.loads(row["messages"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]
    
    def search_conversations(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search conversations using semantic similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            
        Returns:
            List of matching conversations with similarity scores
        """
        results = self.conversations_collection.query(
            query_texts=[query],
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )
        
        conversations = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                
                run_id = metadata.get("run_id")
                if run_id:
                    # Get full conversation from SQLite
                    with self._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT * FROM conversations WHERE run_id = ?",
                            (run_id,)
                        )
                        row = cursor.fetchone()
                        if row:
                            conversations.append({
                                "id": row["id"],
                                "run_id": row["run_id"],
                                "messages": json.loads(row["messages"]),
                                "created_at": row["created_at"],
                                "similarity_score": 1 - distance,
                            })
        
        return conversations
    
    # ==================== Trace Operations ====================
    
    def save_trace(
        self,
        run_id: str,
        action: str,
        details: dict[str, Any],
    ) -> str:
        """Save a trace entry.
        
        Args:
            run_id: The run identifier
            action: The action name
            details: Action details dict
            
        Returns:
            The trace ID
        """
        trace_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO traces (id, run_id, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (trace_id, run_id, action, json.dumps(details), timestamp))
            conn.commit()
        
        return trace_id
    
    def get_traces(
        self,
        run_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get all traces for a run.
        
        Args:
            run_id: The run identifier
            limit: Maximum number of results
            
        Returns:
            List of trace entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM traces WHERE run_id = ? ORDER BY timestamp ASC LIMIT ?",
                (run_id, limit)
            )
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "action": row["action"],
                    "details": json.loads(row["details"]) if row["details"] else {},
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]
    
    def list_traces(
        self,
        limit: int = 100,
        offset: int = 0,
        run_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List traces with optional filtering.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            run_id: Optional run_id filter
            
        Returns:
            List of trace entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if run_id:
                cursor.execute(
                    "SELECT * FROM traces WHERE run_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (run_id, limit, offset)
                )
            else:
                cursor.execute(
                    "SELECT * FROM traces ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            
            rows = cursor.fetchall()
            
            return [
                {
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "action": row["action"],
                    "details": json.loads(row["details"]) if row["details"] else {},
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]
    
    # ==================== Utility Methods ====================
    
    def clear_all(self) -> None:
        """Clear all data from both SQLite and ChromaDB."""
        # Clear SQLite tables
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations")
            cursor.execute("DELETE FROM memories")
            cursor.execute("DELETE FROM traces")
            conn.commit()
        
        # Clear ChromaDB collections
        self.memories_collection.delete(ids=self.memories_collection.get()["ids"])
        self.conversations_collection.delete(ids=self.conversations_collection.get()["ids"])
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about stored data.
        
        Returns:
            Dict with counts and storage info
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conversations_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM memories")
            memories_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM traces")
            traces_count = cursor.fetchone()[0]
        
        return {
            "conversations": conversations_count,
            "memories": memories_count,
            "traces": traces_count,
            "db_path": str(self.db_path),
            "vector_db_path": str(self.vector_db_path),
        }


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
    db_path: Optional[Path] = None,
    vector_db_path: Optional[Path] = None,
) -> MemoryManager:
    """Get or create the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(db_path, vector_db_path)
    return _memory_manager


def init_memory_manager(
    db_path: Optional[Path] = None,
    vector_db_path: Optional[Path] = None,
) -> MemoryManager:
    """Initialize the global memory manager."""
    global _memory_manager
    _memory_manager = MemoryManager(db_path, vector_db_path)
    return _memory_manager
