"""Pytest fixtures for Lantrn Agent Builder tests."""

import asyncio
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import yaml

from lantrn_agent.core.config import ConfigManager, init_config
from lantrn_agent.core.memory import MemoryManager
from lantrn_agent.tools.registry import ToolRegistry


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create directory structure
        (workspace / ".bmad" / "profiles").mkdir(parents=True)
        (workspace / ".bmad" / "blueprints").mkdir(parents=True)
        (workspace / ".bmad" / "runs").mkdir(parents=True)
        (workspace / "agents").mkdir(parents=True)
        (workspace / "policies").mkdir(parents=True)
        (workspace / "config").mkdir(parents=True)
        (workspace / "config" / "profiles").mkdir(parents=True)
        (workspace / "config" / "policies").mkdir(parents=True)
        (workspace / "logs").mkdir(parents=True)
        
        # Create model profiles
        profiles = {
            "fast": {
                "provider": "ollama",
                "model": "llama3.2:3b",
                "ctx_length": 128000,
                "temperature": 0.7,
            },
            "hq": {
                "provider": "ollama",
                "model": "llama3.1:70b",
                "ctx_length": 128000,
                "temperature": 0.3,
            },
        }
        for name, profile in profiles.items():
            with open(workspace / ".bmad" / "profiles" / f"{name}.yaml", "w") as f:
                yaml.dump(profile, f)
        
        # Create default policy in config/policies
        policy = {
            "version": "1.0",
            "name": "default-policy",
            "file_access": {
                "default": "deny",
                "allow": ["workspace/**", "/tmp/**"],
            },
            "network_access": {
                "default": "deny",
                "allow": ["localhost:11434"],
            },
        }
        with open(workspace / "config" / "policies" / "default.yaml", "w") as f:
            yaml.dump(policy, f)
        
        # Create test policy
        test_policy = {
            "version": "1.0",
            "name": "test-policy",
            "file_access": {
                "default": "deny",
                "allow": ["workspace/**", "/tmp/**"],
            },
            "network_access": {
                "default": "deny",
                "allow": ["localhost:11434"],
            },
        }
        with open(workspace / "config" / "policies" / "test.yaml", "w") as f:
            yaml.dump(test_policy, f)
        
        # Create agent definitions
        agent_definitions = {
            "analyst": {
                "role": "analyst",
                "version": "1.0",
                "objective": "Gather and analyze requirements",
                "inputs": ["user_request", "context_files"],
                "outputs": ["requirements_doc", "constraints"],
                "tools": ["document_query", "search_engine"],
                "model_profile": "hq",
                "prompt_template": "You are the Analyst agent.",
                "success_criteria": ["All requirements documented"],
            },
            "pm": {
                "role": "pm",
                "version": "1.0",
                "objective": "Transform requirements into tasks",
                "inputs": ["requirements_doc"],
                "outputs": ["task_list", "acceptance_criteria"],
                "tools": ["document_query", "memory_load"],
                "model_profile": "hq",
                "prompt_template": "You are the PM agent.",
                "success_criteria": ["All tasks defined"],
            },
            "architect": {
                "role": "architect",
                "version": "1.0",
                "objective": "Design technical solution",
                "inputs": ["task_list"],
                "outputs": ["blueprint", "file_specifications"],
                "tools": ["document_query", "code_execution_tool"],
                "model_profile": "hq",
                "prompt_template": "You are the Architect agent.",
                "success_criteria": ["Blueprint complete"],
            },
            "dev": {
                "role": "dev",
                "version": "1.0",
                "objective": "Execute Blueprint and write code",
                "inputs": ["blueprint"],
                "outputs": ["code_changes", "execution_log"],
                "tools": ["code_execution_tool", "file_read", "file_write"],
                "model_profile": "fast",
                "prompt_template": "You are the Dev agent.",
                "success_criteria": ["All tasks executed"],
            },
            "qa": {
                "role": "qa",
                "version": "1.0",
                "objective": "Verify work against acceptance criteria",
                "inputs": ["blueprint", "code_changes"],
                "outputs": ["verification_report", "approval_status"],
                "tools": ["code_execution_tool", "document_query"],
                "model_profile": "hq",
                "prompt_template": "You are the QA agent.",
                "success_criteria": ["All criteria checked"],
            },
        }
        
        for name, definition in agent_definitions.items():
            with open(workspace / "agents" / f"{name}.bmad.yaml", "w") as f:
                yaml.dump(definition, f)
        
        yield workspace


@pytest.fixture
def config_manager(temp_workspace: Path) -> ConfigManager:
    """Create a config manager for testing."""
    return init_config(temp_workspace / "config")


@pytest.fixture
def tool_registry(temp_workspace: Path) -> ToolRegistry:
    """Create a tool registry for testing."""
    return ToolRegistry(temp_workspace)


@pytest.fixture
def memory_manager(temp_workspace: Path) -> MemoryManager:
    """Create a memory manager for testing."""
    return MemoryManager(temp_workspace / ".bmad" / "memory.db")


@pytest.fixture
def agent_yaml_files(temp_workspace: Path) -> Path:
    """Path to agent YAML files (same as temp_workspace/agents)."""
    return temp_workspace / "agents"


@pytest.fixture
def temp_config_dir(temp_workspace: Path) -> Path:
    """Path to config directory."""
    return temp_workspace / "config"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a simple temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_agent_definition_dict() -> dict:
    """Sample agent definition dictionary for testing."""
    return {
        "role": "analyst",
        "version": "1.0",
        "objective": "Analyze requirements for testing",
        "inputs": ["user_request", "context_files"],
        "outputs": ["requirements_doc", "constraints"],
        "tools": ["code_execution", "file_read", "file_write"],
        "model_profile": "fast",
        "prompt_template": "You are a test analyst agent.",
        "success_criteria": ["All requirements documented"],
    }


# =============================================================================
# HTTPX Mock Fixtures for LLM Adapter Tests
# =============================================================================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    client = MagicMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_ollama_chat_response():
    """Mock Ollama chat API response."""
    return {
        "model": "llama3.2:3b",
        "created_at": "2024-01-01T00:00:00Z",
        "message": {
            "role": "assistant",
            "content": "This is a test response from the LLM.",
        },
        "done": True,
        "prompt_eval_count": 10,
        "eval_count": 20,
    }


@pytest.fixture
def mock_ollama_embedding_response():
    """Mock Ollama embedding API response."""
    return {
        "embedding": [0.1] * 768,  # Typical embedding dimension
    }


@pytest.fixture
def mock_ollama_models_response():
    """Mock Ollama list models API response."""
    return {
        "models": [
            {"name": "llama3.2:3b"},
            {"name": "llama3.1:70b"},
        ],
    }
