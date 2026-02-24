"""Tests for agent classes."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from lantrn_agent.agents.base import (
    AgentRole,
    AgentPhase,
    AgentDefinition,
    AgentContext,
    AgentResult,
    BaseAgent,
    AnalystAgent,
    PMAgent,
    ArchitectAgent,
    DevAgent,
    QAAgent,
)
from lantrn_agent.models.llm import Message, MessageRole, ChatResponse


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_agent_role_values(self):
        """Test AgentRole enum values."""
        assert AgentRole.ANALYST == "analyst"
        assert AgentRole.PM == "pm"
        assert AgentRole.ARCHITECT == "architect"
        assert AgentRole.DEV == "dev"
        assert AgentRole.QA == "qa"


class TestAgentPhase:
    """Tests for AgentPhase enum."""

    def test_agent_phase_values(self):
        """Test AgentPhase enum values."""
        assert AgentPhase.PLAN == "plan"
        assert AgentPhase.BUILD == "build"
        assert AgentPhase.VERIFY == "verify"


class TestAgentDefinition:
    """Tests for AgentDefinition dataclass."""

    def test_agent_definition_defaults(self):
        """Test AgentDefinition default values."""
        definition = AgentDefinition(role="analyst")
        assert definition.role == "analyst"
        assert definition.version == "1.0"
        assert definition.objective == ""
        assert definition.inputs == []
        assert definition.outputs == []
        assert definition.tools == []
        assert definition.model_profile == "fast"
        assert definition.prompt_template == ""
        assert definition.success_criteria == []

    def test_agent_definition_custom_values(self):
        """Test AgentDefinition with custom values."""
        definition = AgentDefinition(
            role="dev",
            version="2.0",
            objective="Write code",
            inputs=["blueprint"],
            outputs=["code_changes"],
            tools=["code_execution_tool", "file_write"],
            model_profile="hq",
            prompt_template="You are a developer.",
            success_criteria=["Code compiles", "Tests pass"],
        )
        assert definition.role == "dev"
        assert definition.version == "2.0"
        assert definition.objective == "Write code"
        assert definition.inputs == ["blueprint"]
        assert definition.outputs == ["code_changes"]
        assert "code_execution_tool" in definition.tools
        assert definition.model_profile == "hq"
        assert "developer" in definition.prompt_template
        assert len(definition.success_criteria) == 2

    def test_agent_definition_from_yaml(self, temp_dir: Path, sample_agent_definition_dict: dict):
        """Test AgentDefinition.from_yaml."""
        yaml_path = temp_dir / "agent.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(sample_agent_definition_dict, f)
        
        definition = AgentDefinition.from_yaml(yaml_path)
        
        assert definition.role == "analyst"
        assert definition.version == "1.0"
        assert definition.objective == "Analyze requirements for testing"
        assert "user_request" in definition.inputs
        assert "requirements_doc" in definition.outputs
        assert definition.model_profile == "fast"

    def test_agent_definition_from_yaml_missing_fields(self, temp_dir: Path):
        """Test AgentDefinition.from_yaml with missing optional fields."""
        yaml_path = temp_dir / "minimal_agent.yaml"
        minimal = {"role": "test_agent"}
        with open(yaml_path, "w") as f:
            yaml.dump(minimal, f)
        
        definition = AgentDefinition.from_yaml(yaml_path)
        
        assert definition.role == "test_agent"
        assert definition.version == "1.0"
        assert definition.inputs == []
        assert definition.outputs == []


class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_agent_context_creation(self, temp_workspace: Path):
        """Test AgentContext creation."""
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run-123",
            phase=AgentPhase.PLAN,
        )
        assert context.workspace_path == temp_workspace
        assert context.run_id == "test-run-123"
        assert context.phase == AgentPhase.PLAN
        assert context.inputs == {}
        assert context.memory == {}
        assert context.traces == []

    def test_agent_context_with_inputs(self, temp_workspace: Path):
        """Test AgentContext with inputs."""
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run-123",
            phase=AgentPhase.BUILD,
            inputs={"user_request": "Build a web app"},
        )
        assert context.inputs["user_request"] == "Build a web app"

    def test_agent_context_add_trace(self, temp_workspace: Path):
        """Test AgentContext.add_trace."""
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run-123",
            phase=AgentPhase.PLAN,
        )
        
        context.add_trace("test_action", {"key": "value"})
        
        assert len(context.traces) == 1
        assert context.traces[0]["action"] == "test_action"
        assert context.traces[0]["details"] == {"key": "value"}
        assert "timestamp" in context.traces[0]

    def test_agent_context_multiple_traces(self, temp_workspace: Path):
        """Test AgentContext with multiple traces."""
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run-123",
            phase=AgentPhase.PLAN,
        )
        
        context.add_trace("action1", {"step": 1})
        context.add_trace("action2", {"step": 2})
        context.add_trace("action3", {"step": 3})
        
        assert len(context.traces) == 3
        assert context.traces[0]["action"] == "action1"
        assert context.traces[2]["action"] == "action3"


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_agent_result_defaults(self):
        """Test AgentResult default values."""
        result = AgentResult(success=True)
        assert result.success is True
        assert result.outputs == {}
        assert result.traces == []
        assert result.error is None
        assert result.duration_seconds == 0.0

    def test_agent_result_with_outputs(self):
        """Test AgentResult with outputs."""
        result = AgentResult(
            success=True,
            outputs={"requirements_doc": "Test document"},
        )
        assert result.outputs["requirements_doc"] == "Test document"

    def test_agent_result_with_error(self):
        """Test AgentResult with error."""
        result = AgentResult(
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_agent_result_with_traces(self):
        """Test AgentResult with traces."""
        traces = [
            {"action": "start", "details": {}},
            {"action": "end", "details": {}},
        ]
        result = AgentResult(success=True, traces=traces)
        assert len(result.traces) == 2


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_analyst_agent_role_and_phase(self):
        """Test AnalystAgent has correct role and phase."""
        assert AnalystAgent.role == AgentRole.ANALYST
        assert AnalystAgent.phase == AgentPhase.PLAN

    def test_pm_agent_role_and_phase(self):
        """Test PMAgent has correct role and phase."""
        assert PMAgent.role == AgentRole.PM
        assert PMAgent.phase == AgentPhase.PLAN

    def test_architect_agent_role_and_phase(self):
        """Test ArchitectAgent has correct role and phase."""
        assert ArchitectAgent.role == AgentRole.ARCHITECT
        assert ArchitectAgent.phase == AgentPhase.PLAN

    def test_dev_agent_role_and_phase(self):
        """Test DevAgent has correct role and phase."""
        assert DevAgent.role == AgentRole.DEV
        assert DevAgent.phase == AgentPhase.BUILD

    def test_qa_agent_role_and_phase(self):
        """Test QAAgent has correct role and phase."""
        assert QAAgent.role == AgentRole.QA
        assert QAAgent.phase == AgentPhase.VERIFY

    def test_agent_initialization(self, temp_config_dir: Path):
        """Test agent initialization with definition."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(
            role="analyst",
            objective="Analyze requirements",
            model_profile="fast",
        )
        agent = AnalystAgent(definition)
        
        assert agent.definition == definition
        assert agent.conversation_history == []

    def test_agent_system_prompt(self, temp_config_dir: Path):
        """Test agent system prompt generation."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(
            role="analyst",
            objective="Analyze requirements",
            prompt_template="You are a test agent.",
        )
        agent = AnalystAgent(definition)
        
        prompt = agent.system_prompt()
        assert "test agent" in prompt

    def test_agent_system_prompt_default(self, temp_config_dir: Path):
        """Test agent system prompt with default template."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(
            role="analyst",
            objective="Analyze requirements",
            success_criteria=["Complete analysis", "Clear output"],
        )
        agent = AnalystAgent(definition)
        
        prompt = agent.system_prompt()
        assert "analyst" in prompt
        assert "Analyze requirements" in prompt
        assert "Complete analysis" in prompt

    def test_agent_reset(self, temp_config_dir: Path):
        """Test agent reset clears conversation history."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="analyst")
        agent = AnalystAgent(definition)
        
        agent.conversation_history.append(Message(role=MessageRole.USER, content="Hello"))
        assert len(agent.conversation_history) == 1
        
        agent.reset()
        assert len(agent.conversation_history) == 0


class TestAgentFromYAML:
    """Tests for loading agents from YAML files."""

    def test_load_analyst_from_yaml(self, agent_yaml_files: Path, temp_config_dir: Path):
        """Test loading AnalystAgent from YAML."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        agent_file = agent_yaml_files / "analyst.bmad.yaml"
        agent = BaseAgent.from_yaml(agent_file)
        
        assert isinstance(agent, AnalystAgent)
        assert agent.definition.role == "analyst"
        assert agent.definition.objective == "Gather and analyze requirements"

    def test_load_pm_from_yaml(self, agent_yaml_files: Path, temp_config_dir: Path):
        """Test loading PMAgent from YAML."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        agent_file = agent_yaml_files / "pm.bmad.yaml"
        agent = BaseAgent.from_yaml(agent_file)
        
        assert isinstance(agent, PMAgent)
        assert agent.definition.role == "pm"

    def test_load_architect_from_yaml(self, agent_yaml_files: Path, temp_config_dir: Path):
        """Test loading ArchitectAgent from YAML."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        agent_file = agent_yaml_files / "architect.bmad.yaml"
        agent = BaseAgent.from_yaml(agent_file)
        
        assert isinstance(agent, ArchitectAgent)
        assert agent.definition.role == "architect"

    def test_load_dev_from_yaml(self, agent_yaml_files: Path, temp_config_dir: Path):
        """Test loading DevAgent from YAML."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        agent_file = agent_yaml_files / "dev.bmad.yaml"
        agent = BaseAgent.from_yaml(agent_file)
        
        assert isinstance(agent, DevAgent)
        assert agent.definition.role == "dev"

    def test_load_qa_from_yaml(self, agent_yaml_files: Path, temp_config_dir: Path):
        """Test loading QAAgent from YAML."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        agent_file = agent_yaml_files / "qa.bmad.yaml"
        agent = BaseAgent.from_yaml(agent_file)
        
        assert isinstance(agent, QAAgent)
        assert agent.definition.role == "qa"

    def test_load_unknown_role_from_yaml(self, temp_dir: Path, temp_config_dir: Path):
        """Test loading agent with unknown role raises error."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        yaml_path = temp_dir / "unknown.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump({"role": "unknown_role"}, f)
        
        with pytest.raises(ValueError, match=".*not a valid AgentRole"):
            BaseAgent.from_yaml(yaml_path)


class TestAgentExecute:
    """Tests for agent execute methods."""

    @pytest.mark.asyncio
    async def test_analyst_execute_success(self, temp_workspace: Path, temp_config_dir: Path):
        """Test AnalystAgent execute success."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(
            role="analyst",
            objective="Analyze requirements",
            model_profile="fast",
        )
        agent = AnalystAgent(definition)
        
        # Mock the LLM
        mock_response = ChatResponse(
            content="Requirements document content",
            model="llama3.2:3b",
        )
        agent.chat = AsyncMock(return_value=mock_response)
        
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run",
            phase=AgentPhase.PLAN,
            inputs={"user_request": "Build a web app"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert "requirements_doc" in result.outputs
        assert len(context.traces) > 0

    @pytest.mark.asyncio
    async def test_analyst_execute_with_context_files(self, temp_workspace: Path, temp_config_dir: Path):
        """Test AnalystAgent execute with context files."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="analyst", model_profile="fast")
        agent = AnalystAgent(definition)
        
        mock_response = ChatResponse(
            content="Analysis with context",
            model="llama3.2:3b",
        )
        agent.chat = AsyncMock(return_value=mock_response)
        
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run",
            phase=AgentPhase.PLAN,
            inputs={
                "user_request": "Build app",
                "context_files": ["file1.py", "file2.py"],
            },
        )
        
        result = await agent.execute(context)
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_analyst_execute_error(self, temp_workspace: Path, temp_config_dir: Path):
        """Test AnalystAgent execute handles errors."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="analyst", model_profile="fast")
        agent = AnalystAgent(definition)
        
        agent.chat = AsyncMock(side_effect=Exception("LLM error"))
        
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run",
            phase=AgentPhase.PLAN,
            inputs={"user_request": "Build app"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "LLM error" in result.error

    @pytest.mark.asyncio
    async def test_pm_execute_success(self, temp_workspace: Path, temp_config_dir: Path):
        """Test PMAgent execute success."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="pm", model_profile="fast")
        agent = PMAgent(definition)
        
        mock_response = ChatResponse(
            content="Task list content",
            model="llama3.2:3b",
        )
        agent.chat = AsyncMock(return_value=mock_response)
        
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run",
            phase=AgentPhase.PLAN,
            inputs={"requirements_doc": "Requirements"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert "task_list" in result.outputs

    @pytest.mark.asyncio
    async def test_architect_execute_success(self, temp_workspace: Path, temp_config_dir: Path):
        """Test ArchitectAgent execute success."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="architect", model_profile="hq")
        agent = ArchitectAgent(definition)
        
        mock_response = ChatResponse(
            content="Blueprint content",
            model="llama3.1:70b",
        )
        agent.chat = AsyncMock(return_value=mock_response)
        
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run",
            phase=AgentPhase.PLAN,
            inputs={"task_list": "Tasks"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert "blueprint" in result.outputs

    @pytest.mark.asyncio
    async def test_dev_execute_success(self, temp_workspace: Path, temp_config_dir: Path):
        """Test DevAgent execute success."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="dev", model_profile="fast")
        agent = DevAgent(definition)
        
        mock_response = ChatResponse(
            content="Code changes content",
            model="llama3.2:3b",
        )
        agent.chat = AsyncMock(return_value=mock_response)
        
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run",
            phase=AgentPhase.BUILD,
            inputs={"blueprint": "Blueprint YAML"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert "code_changes" in result.outputs

    @pytest.mark.asyncio
    async def test_qa_execute_success(self, temp_workspace: Path, temp_config_dir: Path):
        """Test QAAgent execute success."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="qa", model_profile="fast")
        agent = QAAgent(definition)
        
        mock_response = ChatResponse(
            content="Verification report content",
            model="llama3.2:3b",
        )
        agent.chat = AsyncMock(return_value=mock_response)
        
        context = AgentContext(
            workspace_path=temp_workspace,
            run_id="test-run",
            phase=AgentPhase.VERIFY,
            inputs={
                "blueprint": "Blueprint",
                "code_changes": "Code",
                "acceptance_criteria": ["Test passes"],
            },
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert "verification_report" in result.outputs


class TestAgentChat:
    """Tests for agent chat methods."""

    @pytest.mark.asyncio
    async def test_agent_chat_adds_to_history(self, temp_config_dir: Path):
        """Test that chat adds messages to history."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="analyst", model_profile="fast")
        agent = AnalystAgent(definition)
        
        # Mock the LLM adapter
        mock_response = ChatResponse(
            content="Response content",
            model="llama3.2:3b",
        )
        agent.llm.chat = AsyncMock(return_value=mock_response)
        
        await agent.chat("Hello")
        
        # Should have system message + user message + assistant message
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0].role == MessageRole.USER
        assert agent.conversation_history[0].content == "Hello"
        assert agent.conversation_history[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_agent_chat_without_history(self, temp_config_dir: Path):
        """Test chat without including history."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="analyst", model_profile="fast")
        agent = AnalystAgent(definition)
        
        mock_response = ChatResponse(
            content="Response",
            model="llama3.2:3b",
        )
        agent.llm.chat = AsyncMock(return_value=mock_response)
        
        await agent.chat("First message", include_history=True)
        await agent.chat("Second message", include_history=False)
        
        # Second message should not include history
        # But both should be added to history
        assert len(agent.conversation_history) == 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_agent_chat_stream(self, temp_config_dir: Path):
        """Test chat_stream method."""
        from lantrn_agent.core.config import init_config
        init_config(temp_config_dir)
        
        definition = AgentDefinition(role="analyst", model_profile="fast")
        agent = AnalystAgent(definition)
        
        async def mock_stream(*args, **kwargs):
            for chunk in ["Hello", " ", "World"]:
                yield chunk
        
        agent.llm.chat_stream = mock_stream
        
        chunks = []
        async for chunk in agent.chat_stream("Test"):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " ", "World"]
        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[1].content == "Hello World"
