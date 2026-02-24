"""Tests for memory system."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lantrn_agent.core.memory import (
    MemoryEntry,
    ConversationEntry,
    TraceEntry,
    MemoryManager,
    get_memory_manager,
    init_memory_manager,
)


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_memory_entry_creation(self):
        """Test MemoryEntry creation."""
        entry = MemoryEntry(
            id="mem-123",
            key="test_key",
            value="Test value",
        )
        
        assert entry.id == "mem-123"
        assert entry.key == "test_key"
        assert entry.value == "Test value"
        assert entry.metadata == {}
        assert entry.embedding_id is None
        assert entry.created_at != ""
        assert entry.updated_at != ""

    def test_memory_entry_with_metadata(self):
        """Test MemoryEntry with metadata."""
        entry = MemoryEntry(
            id="mem-123",
            key="test_key",
            value="Test value",
            metadata={"type": "test", "run_id": "run-123"},
            embedding_id="emb-456",
        )
        
        assert entry.metadata["type"] == "test"
        assert entry.metadata["run_id"] == "run-123"
        assert entry.embedding_id == "emb-456"

    def test_memory_entry_custom_timestamps(self):
        """Test MemoryEntry with custom timestamps."""
        entry = MemoryEntry(
            id="mem-123",
            key="test_key",
            value="Test value",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        
        assert entry.created_at == "2024-01-01T00:00:00"
        assert entry.updated_at == "2024-01-02T00:00:00"


class TestConversationEntry:
    """Tests for ConversationEntry dataclass."""

    def test_conversation_entry_creation(self):
        """Test ConversationEntry creation."""
        entry = ConversationEntry(
            id="conv-123",
            run_id="run-456",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ],
        )
        
        assert entry.id == "conv-123"
        assert entry.run_id == "run-456"
        assert len(entry.messages) == 2
        assert entry.created_at != ""

    def test_conversation_entry_custom_timestamps(self):
        """Test ConversationEntry with custom timestamps."""
        entry = ConversationEntry(
            id="conv-123",
            run_id="run-456",
            messages=[],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )
        
        assert entry.created_at == "2024-01-01T00:00:00"
        assert entry.updated_at == "2024-01-02T00:00:00"


class TestTraceEntry:
    """Tests for TraceEntry dataclass."""

    def test_trace_entry_creation(self):
        """Test TraceEntry creation."""
        entry = TraceEntry(
            id="trace-123",
            run_id="run-456",
            action="agent_start",
            details={"agent": "analyst"},
        )
        
        assert entry.id == "trace-123"
        assert entry.run_id == "run-456"
        assert entry.action == "agent_start"
        assert entry.details["agent"] == "analyst"
        assert entry.timestamp != ""

    def test_trace_entry_custom_timestamp(self):
        """Test TraceEntry with custom timestamp."""
        entry = TraceEntry(
            id="trace-123",
            run_id="run-456",
            action="agent_end",
            details={},
            timestamp="2024-01-01T00:00:00",
        )
        
        assert entry.timestamp == "2024-01-01T00:00:00"


class TestMemoryManager:
    """Tests for MemoryManager class."""

    def test_memory_manager_initialization(self, temp_dir: Path):
        """Test MemoryManager initialization."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        
        manager = MemoryManager(db_path, vector_db_path)
        
        assert manager.db_path == db_path
        assert manager.vector_db_path == vector_db_path
        assert db_path.exists()
        assert vector_db_path.exists()

    def test_memory_manager_creates_tables(self, temp_dir: Path):
        """Test MemoryManager creates SQLite tables."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        
        manager = MemoryManager(db_path, vector_db_path)
        
        # Check tables exist
        with manager._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            
            assert "conversations" in tables
            assert "memories" in tables
            assert "traces" in tables

    def test_memory_manager_creates_indexes(self, temp_dir: Path):
        """Test MemoryManager creates SQLite indexes."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        
        manager = MemoryManager(db_path, vector_db_path)
        
        with manager._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}
            
            assert "idx_conversations_run_id" in indexes
            assert "idx_memories_key" in indexes
            assert "idx_traces_run_id" in indexes


class TestMemoryOperations:
    """Tests for memory CRUD operations."""

    @pytest.fixture
    def memory_manager(self, temp_dir: Path):
        """Create a MemoryManager for testing."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        return MemoryManager(db_path, vector_db_path)

    def test_save_memory(self, memory_manager: MemoryManager):
        """Test saving a memory entry."""
        memory_id = memory_manager.save_memory(
            key="test_key",
            value="Test value",
            metadata={"type": "test"},
        )
        
        assert memory_id is not None
        assert len(memory_id) > 0

    def test_save_memory_with_complex_value(self, memory_manager: MemoryManager):
        """Test saving memory with complex value."""
        complex_value = {
            "name": "test",
            "items": [1, 2, 3],
            "nested": {"key": "value"},
        }
        
        memory_id = memory_manager.save_memory(
            key="complex_key",
            value=json.dumps(complex_value),
            metadata={"type": "complex"},
        )
        
        assert memory_id is not None

    def test_load_memory(self, memory_manager: MemoryManager):
        """Test loading a memory entry."""
        memory_manager.save_memory(
            key="test_key",
            value="Test value",
            metadata={"type": "test"},
        )
        
        memory = memory_manager.load_memory("test_key")
        
        assert memory is not None
        assert memory["key"] == "test_key"
        assert memory["value"] == "Test value"
        assert memory["metadata"]["type"] == "test"

    def test_load_memory_nonexistent(self, memory_manager: MemoryManager):
        """Test loading non-existent memory."""
        memory = memory_manager.load_memory("nonexistent")
        
        assert memory is None

    def test_save_memory_updates_existing(self, memory_manager: MemoryManager):
        """Test saving memory with same key updates it."""
        memory_manager.save_memory(
            key="test_key",
            value="Original value",
            metadata={"version": 1},
        )
        
        memory_manager.save_memory(
            key="test_key",
            value="Updated value",
            metadata={"version": 2},
        )
        
        memory = memory_manager.load_memory("test_key")
        
        assert memory["value"] == "Updated value"
        assert memory["metadata"]["version"] == 2

    def test_delete_memory(self, memory_manager: MemoryManager):
        """Test deleting a memory entry."""
        memory_manager.save_memory(
            key="to_delete",
            value="Delete me",
        )
        
        result = memory_manager.delete_memory("to_delete")
        
        assert result is True
        assert memory_manager.load_memory("to_delete") is None

    def test_delete_memory_nonexistent(self, memory_manager: MemoryManager):
        """Test deleting non-existent memory."""
        result = memory_manager.delete_memory("nonexistent")
        
        assert result is False

    def test_list_memories(self, memory_manager: MemoryManager):
        """Test listing memories."""
        for i in range(5):
            memory_manager.save_memory(
                key=f"key_{i}",
                value=f"value_{i}",
            )
        
        memories = memory_manager.list_memories(limit=3)
        
        assert len(memories) == 3

    def test_list_memories_with_offset(self, memory_manager: MemoryManager):
        """Test listing memories with offset."""
        for i in range(5):
            memory_manager.save_memory(
                key=f"key_{i}",
                value=f"value_{i}",
            )
        
        first_page = memory_manager.list_memories(limit=2, offset=0)
        second_page = memory_manager.list_memories(limit=2, offset=2)
        
        assert len(first_page) == 2
        assert len(second_page) == 2
        # Keys should be different
        first_keys = {m["key"] for m in first_page}
        second_keys = {m["key"] for m in second_page}
        assert first_keys.isdisjoint(second_keys)


class TestConversationOperations:
    """Tests for conversation CRUD operations."""

    @pytest.fixture
    def memory_manager(self, temp_dir: Path):
        """Create a MemoryManager for testing."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        return MemoryManager(db_path, vector_db_path)

    def test_save_conversation(self, memory_manager: MemoryManager):
        """Test saving a conversation."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        
        conv_id = memory_manager.save_conversation(
            run_id="run-123",
            messages=messages,
        )
        
        assert conv_id is not None

    def test_get_conversation(self, memory_manager: MemoryManager):
        """Test getting a conversation."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        
        memory_manager.save_conversation(
            run_id="run-123",
            messages=messages,
        )
        
        retrieved = memory_manager.get_conversation("run-123")
        
        assert len(retrieved) == 2
        assert retrieved[0]["role"] == "user"
        assert retrieved[0]["content"] == "Hello"

    def test_get_conversation_nonexistent(self, memory_manager: MemoryManager):
        """Test getting non-existent conversation."""
        retrieved = memory_manager.get_conversation("nonexistent")
        
        assert retrieved == []

    def test_save_conversation_updates_existing(self, memory_manager: MemoryManager):
        """Test saving conversation with same run_id updates it."""
        messages1 = [{"role": "user", "content": "Hello"}]
        messages2 = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        
        memory_manager.save_conversation("run-123", messages1)
        memory_manager.save_conversation("run-123", messages2)
        
        retrieved = memory_manager.get_conversation("run-123")
        
        assert len(retrieved) == 2

    def test_list_conversations(self, memory_manager: MemoryManager):
        """Test listing conversations."""
        for i in range(3):
            memory_manager.save_conversation(
                run_id=f"run-{i}",
                messages=[{"role": "user", "content": f"Message {i}"}],
            )
        
        conversations = memory_manager.list_conversations(limit=2)
        
        assert len(conversations) == 2


class TestTraceOperations:
    """Tests for trace CRUD operations."""

    @pytest.fixture
    def memory_manager(self, temp_dir: Path):
        """Create a MemoryManager for testing."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        return MemoryManager(db_path, vector_db_path)

    def test_save_trace(self, memory_manager: MemoryManager):
        """Test saving a trace entry."""
        trace_id = memory_manager.save_trace(
            run_id="run-123",
            action="agent_start",
            details={"agent": "analyst"},
        )
        
        assert trace_id is not None

    def test_get_traces(self, memory_manager: MemoryManager):
        """Test getting traces for a run."""
        memory_manager.save_trace("run-123", "start", {"step": 1})
        memory_manager.save_trace("run-123", "end", {"step": 2})
        memory_manager.save_trace("run-456", "start", {"step": 1})
        
        traces = memory_manager.get_traces("run-123")
        
        assert len(traces) == 2
        assert traces[0]["action"] == "start"
        assert traces[1]["action"] == "end"

    def test_get_traces_empty(self, memory_manager: MemoryManager):
        """Test getting traces for non-existent run."""
        traces = memory_manager.get_traces("nonexistent")
        
        assert traces == []

    def test_list_traces(self, memory_manager: MemoryManager):
        """Test listing all traces."""
        for i in range(5):
            memory_manager.save_trace(
                run_id=f"run-{i % 2}",
                action=f"action_{i}",
                details={"index": i},
            )
        
        traces = memory_manager.list_traces(limit=3)
        
        assert len(traces) == 3

    def test_list_traces_by_run(self, memory_manager: MemoryManager):
        """Test listing traces filtered by run_id."""
        memory_manager.save_trace("run-1", "action_1", {})
        memory_manager.save_trace("run-1", "action_2", {})
        memory_manager.save_trace("run-2", "action_3", {})
        
        traces = memory_manager.list_traces(run_id="run-1")
        
        assert len(traces) == 2
        for trace in traces:
            assert trace["run_id"] == "run-1"


class TestSemanticSearch:
    """Tests for semantic search operations."""

    @pytest.fixture
    def memory_manager(self, temp_dir: Path):
        """Create a MemoryManager for testing."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        return MemoryManager(db_path, vector_db_path)

    def test_search_memories(self, memory_manager: MemoryManager):
        """Test searching memories."""
        memory_manager.save_memory(
            key="python_code",
            value="Python code for web scraping",
            metadata={"type": "code"},
        )
        memory_manager.save_memory(
            key="javascript_code",
            value="JavaScript code for frontend",
            metadata={"type": "code"},
        )
        
        results = memory_manager.search_memories("python scraping", limit=5)
        
        # Results may vary based on embedding quality
        assert isinstance(results, list)

    def test_search_memories_with_filter(self, memory_manager: MemoryManager):
        """Test searching memories with metadata filter."""
        memory_manager.save_memory(
            key="doc_1",
            value="API documentation",
            metadata={"type": "docs", "category": "api"},
        )
        memory_manager.save_memory(
            key="doc_2",
            value="User guide",
            metadata={"type": "docs", "category": "guide"},
        )
        
        results = memory_manager.search_memories(
            "documentation",
            limit=5,
            metadata_filter={"type": "docs"},
        )
        
        assert isinstance(results, list)

    def test_search_conversations(self, memory_manager: MemoryManager):
        """Test searching conversations."""
        memory_manager.save_conversation(
            "run-1",
            [
                {"role": "user", "content": "How to build a REST API?"},
                {"role": "assistant", "content": "Use FastAPI for Python."},
            ],
        )
        memory_manager.save_conversation(
            "run-2",
            [
                {"role": "user", "content": "How to create a frontend?"},
                {"role": "assistant", "content": "Use React for UI."},
            ],
        )
        
        results = memory_manager.search_conversations("REST API", limit=5)
        
        assert isinstance(results, list)


class TestUtilityMethods:
    """Tests for utility methods."""

    @pytest.fixture
    def memory_manager(self, temp_dir: Path):
        """Create a MemoryManager for testing."""
        db_path = temp_dir / "test.db"
        vector_db_path = temp_dir / "chroma"
        return MemoryManager(db_path, vector_db_path)

    def test_clear_all(self, memory_manager: MemoryManager):
        """Test clearing all data."""
        memory_manager.save_memory("key1", "value1")
        memory_manager.save_conversation("run-1", [{"role": "user", "content": "test"}])
        memory_manager.save_trace("run-1", "action", {})
        
        memory_manager.clear_all()
        
        assert memory_manager.load_memory("key1") is None
        assert memory_manager.get_conversation("run-1") == []
        assert memory_manager.get_traces("run-1") == []

    def test_get_stats(self, memory_manager: MemoryManager):
        """Test getting statistics."""
        memory_manager.save_memory("key1", "value1")
        memory_manager.save_memory("key2", "value2")
        memory_manager.save_conversation("run-1", [{"role": "user", "content": "test"}])
        memory_manager.save_trace("run-1", "action", {})
        memory_manager.save_trace("run-1", "action2", {})
        
        stats = memory_manager.get_stats()
        
        assert stats["memories"] == 2
        assert stats["conversations"] == 1
        assert stats["traces"] == 2
        assert "db_path" in stats
        assert "vector_db_path" in stats


class TestGlobalMemoryManager:
    """Tests for global memory manager functions."""

    def test_get_memory_manager_creates_instance(self, temp_dir: Path):
        """Test get_memory_manager creates instance."""
        import lantrn_agent.core.memory as memory_module
        memory_module._memory_manager = None
        
        manager = get_memory_manager(
            db_path=temp_dir / "test.db",
            vector_db_path=temp_dir / "chroma",
        )
        
        assert isinstance(manager, MemoryManager)

    def test_get_memory_manager_returns_same_instance(self, temp_dir: Path):
        """Test get_memory_manager returns same instance."""
        import lantrn_agent.core.memory as memory_module
        memory_module._memory_manager = None
        
        manager1 = get_memory_manager(
            db_path=temp_dir / "test1.db",
            vector_db_path=temp_dir / "chroma1",
        )
        manager2 = get_memory_manager()
        
        assert manager1 is manager2

    def test_init_memory_manager_creates_new_instance(self, temp_dir: Path):
        """Test init_memory_manager creates new instance."""
        import lantrn_agent.core.memory as memory_module
        memory_module._memory_manager = None
        
        manager = init_memory_manager(
            db_path=temp_dir / "test2.db",
            vector_db_path=temp_dir / "chroma2",
        )
        
        assert isinstance(manager, MemoryManager)
        assert manager.db_path == temp_dir / "test2.db"

    def test_init_memory_manager_updates_global(self, temp_dir: Path):
        """Test init_memory_manager updates global instance."""
        import lantrn_agent.core.memory as memory_module
        memory_module._memory_manager = None
        
        manager = init_memory_manager(
            db_path=temp_dir / "test3.db",
            vector_db_path=temp_dir / "chroma3",
        )
        global_manager = get_memory_manager()
        
        assert manager is global_manager
