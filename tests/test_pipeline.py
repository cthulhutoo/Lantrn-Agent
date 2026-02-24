"""Tests for pipeline orchestration."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from lantrn_agent.core.pipeline import Blueprint, RunManifest, Pipeline
from lantrn_agent.agents.base import (
    AgentContext,
    AgentPhase,
    AgentResult,
    AgentRole,
)


class TestBlueprint:
    """Tests for Blueprint dataclass."""

    def test_blueprint_creation(self):
        """Test Blueprint creation."""
        blueprint = Blueprint(
            id="bp-123",
            created_at="2024-01-01T00:00:00",
            user_request="Build a web app",
            requirements={"doc": "Requirements"},
            tasks=[{"id": "1", "description": "Task 1"}],
            files=[{"path": "main.py", "description": "Main file"}],
            tool_budgets={"code_execution": 100},
            architecture_decisions=["Use FastAPI"],
        )
        
        assert blueprint.id == "bp-123"
        assert blueprint.user_request == "Build a web app"
        assert len(blueprint.tasks) == 1
        assert len(blueprint.files) == 1
        assert blueprint.architecture_decisions[0] == "Use FastAPI"

    def test_blueprint_to_yaml(self):
        """Test Blueprint.to_yaml."""
        blueprint = Blueprint(
            id="bp-123",
            created_at="2024-01-01T00:00:00",
            user_request="Build a web app",
            requirements={"doc": "Requirements"},
            tasks=[{"id": "1", "description": "Task 1"}],
            files=[{"path": "main.py"}],
            tool_budgets={"code_execution": 100},
            architecture_decisions=["Use FastAPI"],
        )
        
        yaml_str = blueprint.to_yaml()
        
        assert "id: bp-123" in yaml_str
        assert "user_request: Build a web app" in yaml_str
        assert "Use FastAPI" in yaml_str

    def test_blueprint_from_yaml(self):
        """Test Blueprint.from_yaml."""
        yaml_str = """
id: bp-456
created_at: "2024-01-01T00:00:00"
user_request: Create an API
requirements:
  doc: Requirements doc
tasks:
  - id: "1"
    description: Task 1
files:
  - path: api.py
tool_budgets:
  code_execution: 50
architecture_decisions:
  - Use FastAPI
"""
        blueprint = Blueprint.from_yaml(yaml_str)
        
        assert blueprint.id == "bp-456"
        assert blueprint.user_request == "Create an API"
        assert len(blueprint.tasks) == 1
        assert blueprint.tool_budgets["code_execution"] == 50

    def test_blueprint_roundtrip(self):
        """Test Blueprint YAML roundtrip."""
        original = Blueprint(
            id="bp-789",
            created_at="2024-01-01T00:00:00",
            user_request="Test request",
            requirements={"key": "value"},
            tasks=[{"id": "1", "desc": "Task"}],
            files=[{"path": "test.py"}],
            tool_budgets={"memory": 1000},
            architecture_decisions=["Decision 1"],
        )
        
        yaml_str = original.to_yaml()
        restored = Blueprint.from_yaml(yaml_str)
        
        assert restored.id == original.id
        assert restored.user_request == original.user_request
        assert restored.requirements == original.requirements
        assert restored.tasks == original.tasks


class TestRunManifest:
    """Tests for RunManifest dataclass."""

    def test_run_manifest_creation(self):
        """Test RunManifest creation."""
        manifest = RunManifest(
            id="run-123",
            blueprint_id="bp-123",
            started_at="2024-01-01T00:00:00",
            status="completed",
            phase="build",
        )
        
        assert manifest.id == "run-123"
        assert manifest.blueprint_id == "bp-123"
        assert manifest.status == "completed"
        assert manifest.phase == "build"
        assert manifest.completed_at is None
        assert manifest.error is None

    def test_run_manifest_with_results(self):
        """Test RunManifest with agent results."""
        dev_result = AgentResult(
            success=True,
            outputs={"code_changes": "Changes made"},
        )
        
        manifest = RunManifest(
            id="run-123",
            blueprint_id="bp-123",
            started_at="2024-01-01T00:00:00",
            status="completed",
            phase="build",
            agent_results={"dev": dev_result},
        )
        
        assert "dev" in manifest.agent_results
        assert manifest.agent_results["dev"].success is True

    def test_run_manifest_to_dict(self):
        """Test RunManifest.to_dict."""
        dev_result = AgentResult(
            success=True,
            outputs={"code": "test"},
        )
        
        manifest = RunManifest(
            id="run-123",
            blueprint_id="bp-123",
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:05:00",
            status="completed",
            phase="build",
            agent_results={"dev": dev_result},
            traces=[{"action": "start"}],
        )
        
        data = manifest.to_dict()
        
        assert data["id"] == "run-123"
        assert data["blueprint_id"] == "bp-123"
        assert data["status"] == "completed"
        assert data["phase"] == "build"
        assert "dev" in data["agent_results"]
        assert len(data["traces"]) == 1

    def test_run_manifest_with_error(self):
        """Test RunManifest with error."""
        manifest = RunManifest(
            id="run-123",
            blueprint_id="bp-123",
            started_at="2024-01-01T00:00:00",
            status="failed",
            phase="build",
            error="Something went wrong",
        )
        
        assert manifest.status == "failed"
        assert manifest.error == "Something went wrong"


class TestPipeline:
    """Tests for Pipeline class."""

    def test_pipeline_initialization(self, temp_workspace: Path):
        """Test Pipeline initialization."""
        pipeline = Pipeline(temp_workspace)
        
        assert pipeline.workspace_path == temp_workspace
        assert pipeline.tool_registry is not None
        assert pipeline.blueprints_dir.exists()
        assert pipeline.runs_dir.exists()

    def test_pipeline_custom_directories(self, temp_workspace: Path):
        """Test Pipeline with custom agents directory."""
        agents_dir = temp_workspace / "custom_agents"
        agents_dir.mkdir()
        
        pipeline = Pipeline(temp_workspace, agents_dir=agents_dir)
        
        assert pipeline.agents_dir == agents_dir

    def test_pipeline_load_agent(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.load_agent."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        pipeline = Pipeline(temp_workspace, agents_dir=agent_yaml_files)
        
        agent = pipeline.load_agent(AgentRole.ANALYST)
        
        assert agent is not None
        assert agent.definition.role == "analyst"

    def test_pipeline_load_agent_caches(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.load_agent caches agents."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        pipeline = Pipeline(temp_workspace, agents_dir=agent_yaml_files)
        
        agent1 = pipeline.load_agent(AgentRole.ANALYST)
        agent2 = pipeline.load_agent(AgentRole.ANALYST)  # QA agent not created in temp_workspace
        
        assert agent1 is agent2

    def test_pipeline_load_agent_not_found(self, temp_workspace: Path, temp_config_dir: Path):
        """Test Pipeline.load_agent raises error if not found."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        # Delete the QA agent file to test error handling
        qa_agent_file = temp_workspace / "agents" / "qa.bmad.yaml"
        if qa_agent_file.exists():
            qa_agent_file.unlink()
        
        pipeline = Pipeline(temp_workspace)
        
        with pytest.raises(FileNotFoundError, match="Agent definition not found"):
            pipeline.load_agent(AgentRole.QA)

    @pytest.mark.asyncio
    async def test_pipeline_plan(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.plan method."""
        from lantrn_agent.core.config import init_config
        from lantrn_agent.core.memory import MemoryManager
        init_config(temp_config_dir)
        
        # Create mock memory manager
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.save_memory = MagicMock()
        mock_memory.save_trace = MagicMock()
        mock_memory.save_conversation = MagicMock()
        
        pipeline = Pipeline(
            temp_workspace,
            agents_dir=agent_yaml_files,
            memory_manager=mock_memory,
        )
        
        # Mock agents
        for role in [AgentRole.ANALYST, AgentRole.PM, AgentRole.ARCHITECT]:
            agent = pipeline.load_agent(role)
            agent.execute = AsyncMock(return_value=AgentResult(
                success=True,
                outputs={"requirements_doc": "Test doc"},
            ))
        
        blueprint = await pipeline.plan("Build a web app")
        
        assert blueprint is not None
        assert blueprint.user_request == "Build a web app"
        assert blueprint.id is not None

    @pytest.mark.asyncio
    async def test_pipeline_plan_analyst_failure(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.plan handles analyst failure."""
        from lantrn_agent.core.config import init_config
        from lantrn_agent.core.memory import MemoryManager
        init_config(temp_config_dir)
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.save_memory = MagicMock()
        mock_memory.save_trace = MagicMock()
        mock_memory.save_conversation = MagicMock()
        
        pipeline = Pipeline(
            temp_workspace,
            agents_dir=agent_yaml_files,
            memory_manager=mock_memory,
        )
        
        # Mock analyst to fail
        analyst = pipeline.load_agent(AgentRole.QA)  # QA agent not created in temp_workspace
        analyst.execute = AsyncMock(return_value=AgentResult(
            success=False,
            error="Analyst failed",
        ))
        
        with pytest.raises(RuntimeError, match="Analyst failed"):
            await pipeline.plan("Build a web app")

    @pytest.mark.asyncio
    async def test_pipeline_build(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.build method."""
        from lantrn_agent.core.config import init_config
        from lantrn_agent.core.memory import MemoryManager
        init_config(temp_config_dir)
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.save_memory = MagicMock()
        mock_memory.save_trace = MagicMock()
        mock_memory.save_conversation = MagicMock()
        
        pipeline = Pipeline(
            temp_workspace,
            agents_dir=agent_yaml_files,
            memory_manager=mock_memory,
        )
        
        # Mock dev agent
        dev = pipeline.load_agent(AgentRole.DEV)
        dev.execute = AsyncMock(return_value=AgentResult(
            success=True,
            outputs={"code_changes": "Changes made"},
        ))
        
        blueprint = Blueprint(
            id="bp-123",
            created_at="2024-01-01T00:00:00",
            user_request="Build app",
            requirements={},
            tasks=[],
            files=[],
            tool_budgets={},
            architecture_decisions=[],
        )
        
        manifest = await pipeline.build(blueprint)
        
        assert manifest is not None
        assert manifest.status == "completed"
        assert manifest.phase == "build"
        assert "dev" in manifest.agent_results

    @pytest.mark.asyncio
    async def test_pipeline_build_failure(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.build handles failure."""
        from lantrn_agent.core.config import init_config
        from lantrn_agent.core.memory import MemoryManager
        init_config(temp_config_dir)
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.save_memory = MagicMock()
        mock_memory.save_trace = MagicMock()
        mock_memory.save_conversation = MagicMock()
        
        pipeline = Pipeline(
            temp_workspace,
            agents_dir=agent_yaml_files,
            memory_manager=mock_memory,
        )
        
        dev = pipeline.load_agent(AgentRole.DEV)
        dev.execute = AsyncMock(return_value=AgentResult(
            success=False,
            error="Build failed",
        ))
        
        blueprint = Blueprint(
            id="bp-123",
            created_at="2024-01-01T00:00:00",
            user_request="Build app",
            requirements={},
            tasks=[],
            files=[],
            tool_budgets={},
            architecture_decisions=[],
        )
        
        manifest = await pipeline.build(blueprint)
        
        assert manifest.status == "failed"
        assert manifest.error == "Build failed"

    @pytest.mark.asyncio
    async def test_pipeline_verify(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.verify method."""
        from lantrn_agent.core.config import init_config
        from lantrn_agent.core.memory import MemoryManager
        init_config(temp_config_dir)
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.save_memory = MagicMock()
        mock_memory.save_trace = MagicMock()
        mock_memory.save_conversation = MagicMock()
        
        pipeline = Pipeline(
            temp_workspace,
            agents_dir=agent_yaml_files,
            memory_manager=mock_memory,
        )
        
        # Mock QA agent
        qa = pipeline.load_agent(AgentRole.QA)
        qa.execute = AsyncMock(return_value=AgentResult(
            success=True,
            outputs={"verification_report": "All tests pass"},
        ))
        
        blueprint = Blueprint(
            id="bp-123",
            created_at="2024-01-01T00:00:00",
            user_request="Build app",
            requirements={},
            tasks=[],
            files=[],
            tool_budgets={},
            architecture_decisions=[],
        )
        
        build_manifest = RunManifest(
            id="run-123",
            blueprint_id="bp-123",
            started_at="2024-01-01T00:00:00",
            status="completed",
            phase="build",
            agent_results={
                "dev": AgentResult(success=True, outputs={"code_changes": "Changes"})
            },
        )
        
        manifest = await pipeline.verify(blueprint, build_manifest)
        
        assert manifest is not None
        assert manifest.status == "approved"
        assert manifest.phase == "verify"
        assert "qa" in manifest.agent_results

    @pytest.mark.asyncio
    async def test_pipeline_verify_rejection(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.verify handles rejection."""
        from lantrn_agent.core.config import init_config
        from lantrn_agent.core.memory import MemoryManager
        init_config(temp_config_dir)
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.save_memory = MagicMock()
        mock_memory.save_trace = MagicMock()
        mock_memory.save_conversation = MagicMock()
        
        pipeline = Pipeline(
            temp_workspace,
            agents_dir=agent_yaml_files,
            memory_manager=mock_memory,
        )
        
        qa = pipeline.load_agent(AgentRole.QA)
        qa.execute = AsyncMock(return_value=AgentResult(
            success=False,
            error="Tests failed",
        ))
        
        blueprint = Blueprint(
            id="bp-123",
            created_at="2024-01-01T00:00:00",
            user_request="Build app",
            requirements={},
            tasks=[],
            files=[],
            tool_budgets={},
            architecture_decisions=[],
        )
        
        build_manifest = RunManifest(
            id="run-123",
            blueprint_id="bp-123",
            started_at="2024-01-01T00:00:00",
            status="completed",
            phase="build",
            agent_results={
                "dev": AgentResult(success=True, outputs={"code_changes": "Changes"})
            },
        )
        
        manifest = await pipeline.verify(blueprint, build_manifest)
        
        assert manifest.status == "rejected"

    @pytest.mark.asyncio
    async def test_pipeline_run_full(self, temp_workspace: Path, agent_yaml_files: Path, temp_config_dir: Path):
        """Test Pipeline.run full pipeline."""
        from lantrn_agent.core.config import init_config
        from lantrn_agent.core.memory import MemoryManager
        init_config(temp_config_dir)
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.save_memory = MagicMock()
        mock_memory.save_trace = MagicMock()
        mock_memory.save_conversation = MagicMock()
        
        pipeline = Pipeline(
            temp_workspace,
            agents_dir=agent_yaml_files,
            memory_manager=mock_memory,
        )
        
        # Mock all agents
        for role in [AgentRole.ANALYST, AgentRole.PM, AgentRole.ARCHITECT, AgentRole.DEV, AgentRole.QA]:
            agent = pipeline.load_agent(role)
            agent.execute = AsyncMock(return_value=AgentResult(
                success=True,
                outputs={"result": "test"},
            ))
        
        blueprint, build_manifest, verify_manifest = await pipeline.run("Build a web app")
        
        assert blueprint is not None
        assert build_manifest is not None
        assert verify_manifest is not None
        assert build_manifest.phase == "build"
        assert verify_manifest.phase == "verify"


class TestPipelineMemoryMethods:
    """Tests for Pipeline memory query methods."""

    def test_search_past_requests(self, temp_workspace: Path):
        """Test Pipeline.search_past_requests."""
        from lantrn_agent.core.memory import MemoryManager
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.search_memories = MagicMock(return_value=[
            {"key": "request_1", "value": "Build app"},
        ])
        
        pipeline = Pipeline(temp_workspace, memory_manager=mock_memory)
        results = pipeline.search_past_requests("build app")
        
        assert len(results) == 1
        mock_memory.search_memories.assert_called_once()

    def test_search_past_blueprints(self, temp_workspace: Path):
        """Test Pipeline.search_past_blueprints."""
        from lantrn_agent.core.memory import MemoryManager
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.search_memories = MagicMock(return_value=[
            {"key": "blueprint_1", "value": "Blueprint YAML"},
        ])
        
        pipeline = Pipeline(temp_workspace, memory_manager=mock_memory)
        results = pipeline.search_past_blueprints("web app")
        
        assert len(results) == 1

    def test_get_run_traces(self, temp_workspace: Path):
        """Test Pipeline.get_run_traces."""
        from lantrn_agent.core.memory import MemoryManager
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.get_traces = MagicMock(return_value=[
            {"action": "start", "details": {}},
        ])
        
        pipeline = Pipeline(temp_workspace, memory_manager=mock_memory)
        traces = pipeline.get_run_traces("run-123")
        
        assert len(traces) == 1
        mock_memory.get_traces.assert_called_with("run-123")

    def test_get_run_conversation(self, temp_workspace: Path):
        """Test Pipeline.get_run_conversation."""
        from lantrn_agent.core.memory import MemoryManager
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.get_conversation = MagicMock(return_value=[
            {"role": "user", "content": "Hello"},
        ])
        
        pipeline = Pipeline(temp_workspace, memory_manager=mock_memory)
        conversation = pipeline.get_run_conversation("run-123", "analyst")
        
        assert len(conversation) == 1
        mock_memory.get_conversation.assert_called_with("run-123_analyst")

    def test_get_memory_stats(self, temp_workspace: Path):
        """Test Pipeline.get_memory_stats."""
        from lantrn_agent.core.memory import MemoryManager
        
        mock_memory = MagicMock(spec=MemoryManager)
        mock_memory.get_stats = MagicMock(return_value={
            "memories": 10,
            "conversations": 5,
            "traces": 20,
        })
        
        pipeline = Pipeline(temp_workspace, memory_manager=mock_memory)
        stats = pipeline.get_memory_stats()
        
        assert stats["memories"] == 10
        assert stats["conversations"] == 5
        assert stats["traces"] == 20
