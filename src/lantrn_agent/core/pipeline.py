"""BMad Pipeline Orchestrator.

Implements the Plan → Build → Verify workflow.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import yaml

from ..agents.base import (
    AgentContext,
    AgentPhase,
    AgentResult,
    AgentRole,
    AnalystAgent,
    ArchitectAgent,
    BaseAgent,
    DevAgent,
    PMAgent,
    QAAgent,
)
from ..core.config import get_config
from ..core.memory import MemoryManager, get_memory_manager
from ..tools.registry import ToolRegistry


@dataclass
class Blueprint:
    """Blueprint produced by the Plan phase."""
    id: str
    created_at: str
    user_request: str
    requirements: dict[str, Any]
    tasks: list[dict[str, Any]]
    files: list[dict[str, Any]]
    tool_budgets: dict[str, int]
    architecture_decisions: list[str]
    
    def to_yaml(self) -> str:
        """Serialize blueprint to YAML."""
        return yaml.dump({
            "id": self.id,
            "created_at": self.created_at,
            "user_request": self.user_request,
            "requirements": self.requirements,
            "tasks": self.tasks,
            "files": self.files,
            "tool_budgets": self.tool_budgets,
            "architecture_decisions": self.architecture_decisions,
        })
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Blueprint":
        """Deserialize blueprint from YAML."""
        data = yaml.safe_load(yaml_str)
        return cls(**data)


@dataclass
class RunManifest:
    """Manifest for a pipeline run."""
    id: str
    blueprint_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "pending"
    phase: str = "plan"
    agent_results: dict[str, AgentResult] = field(default_factory=dict)
    traces: list[dict] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Serialize manifest to dict."""
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "phase": self.phase,
            "agent_results": {
                k: {"success": v.success, "outputs": v.outputs, "error": v.error}
                for k, v in self.agent_results.items()
            },
            "traces": self.traces,
            "error": self.error,
        }


class Pipeline:
    """BMad Pipeline orchestrator with persistent memory."""
    
    def __init__(
        self,
        workspace_path: Path,
        agents_dir: Optional[Path] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.workspace_path = workspace_path
        self.config = get_config()
        self.agents_dir = agents_dir or workspace_path / "agents"
        self.tool_registry = ToolRegistry(workspace_path)
        
        # Initialize memory manager
        self.memory = memory_manager or get_memory_manager(
            db_path=workspace_path / ".bmad" / "memory.db",
            vector_db_path=workspace_path / ".bmad" / "chroma_db",
        )
        
        # Create directories
        self.blueprints_dir = workspace_path / ".bmad" / "blueprints"
        self.runs_dir = workspace_path / ".bmad" / "runs"
        self.blueprints_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        
        # Loaded agents
        self._agents: dict[AgentRole, BaseAgent] = {}
    
    def load_agent(self, role: AgentRole) -> BaseAgent:
        """Load an agent from YAML definition."""
        if role in self._agents:
            return self._agents[role]
        
        agent_file = self.agents_dir / f"{role.value}.bmad.yaml"
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent definition not found: {agent_file}")
        
        agent = BaseAgent.from_yaml(agent_file)
        self._agents[role] = agent
        return agent
    
    def _save_traces(self, run_id: str, traces: list[dict]) -> None:
        """Save traces to memory system."""
        for trace in traces:
            self.memory.save_trace(
                run_id=run_id,
                action=trace.get("action", "unknown"),
                details=trace.get("details", {}),
            )
    
    def _save_conversation(
        self,
        run_id: str,
        agent: BaseAgent,
        phase: str,
    ) -> None:
        """Save agent conversation to memory system."""
        messages = [
            {
                "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                "content": msg.content,
            }
            for msg in agent.conversation_history
        ]
        
        if messages:
            # Save with composite key for phase-specific conversations
            self.memory.save_conversation(
                run_id=f"{run_id}_{phase}",
                messages=messages,
            )
    
    async def plan(
        self,
        user_request: str,
        context_files: Optional[list[str]] = None,
    ) -> Blueprint:
        """Execute the Plan phase: Analyst → PM → Architect."""
        run_id = str(uuid.uuid4())[:8]
        
        # Save initial request as memory
        self.memory.save_memory(
            key=f"request_{run_id}",
            value=user_request,
            metadata={"type": "user_request", "phase": "plan", "run_id": run_id},
        )
        
        # Initialize context
        context = AgentContext(
            workspace_path=self.workspace_path,
            run_id=run_id,
            phase=AgentPhase.PLAN,
            inputs={
                "user_request": user_request,
                "context_files": context_files or [],
            },
        )
        
        # Run Analyst
        analyst = self.load_agent(AgentRole.ANALYST)
        analyst_result = await analyst.execute(context)
        
        # Save analyst traces and conversation
        self._save_traces(run_id, context.traces)
        self._save_conversation(run_id, analyst, "analyst")
        
        if not analyst_result.success:
            # Save error to memory
            self.memory.save_memory(
                key=f"error_{run_id}_analyst",
                value=analyst_result.error or "Unknown error",
                metadata={"type": "error", "phase": "plan", "agent": "analyst", "run_id": run_id},
            )
            raise RuntimeError(f"Analyst failed: {analyst_result.error}")
        
        context.inputs["requirements_doc"] = analyst_result.outputs.get("requirements_doc", "")
        
        # Run PM
        pm = self.load_agent(AgentRole.PM)
        pm_result = await pm.execute(context)
        
        # Save PM traces and conversation
        self._save_traces(run_id, context.traces)
        self._save_conversation(run_id, pm, "pm")
        
        if not pm_result.success:
            self.memory.save_memory(
                key=f"error_{run_id}_pm",
                value=pm_result.error or "Unknown error",
                metadata={"type": "error", "phase": "plan", "agent": "pm", "run_id": run_id},
            )
            raise RuntimeError(f"PM failed: {pm_result.error}")
        
        context.inputs["task_list"] = pm_result.outputs.get("task_list", "")
        context.inputs["acceptance_criteria"] = pm_result.outputs.get("acceptance_criteria", [])
        
        # Run Architect
        architect = self.load_agent(AgentRole.ARCHITECT)
        architect_result = await architect.execute(context)
        
        # Save architect traces and conversation
        self._save_traces(run_id, context.traces)
        self._save_conversation(run_id, architect, "architect")
        
        if not architect_result.success:
            self.memory.save_memory(
                key=f"error_{run_id}_architect",
                value=architect_result.error or "Unknown error",
                metadata={"type": "error", "phase": "plan", "agent": "architect", "run_id": run_id},
            )
            raise RuntimeError(f"Architect failed: {architect_result.error}")
        
        # Create Blueprint
        blueprint = Blueprint(
            id=str(uuid.uuid4())[:8],
            created_at=datetime.utcnow().isoformat(),
            user_request=user_request,
            requirements=analyst_result.outputs,
            tasks=[],  # Parse from PM output
            files=[],  # Parse from Architect output
            tool_budgets={},
            architecture_decisions=[],
        )
        
        # Save blueprint to memory
        self.memory.save_memory(
            key=f"blueprint_{blueprint.id}",
            value=blueprint.to_yaml(),
            metadata={
                "type": "blueprint",
                "run_id": run_id,
                "user_request": user_request[:200],  # Truncate for metadata
            },
        )
        
        # Save blueprint to file
        blueprint_path = self.blueprints_dir / f"{blueprint.id}.yaml"
        with open(blueprint_path, "w") as f:
            f.write(blueprint.to_yaml())
        
        return blueprint
    
    async def build(
        self,
        blueprint: Blueprint,
    ) -> RunManifest:
        """Execute the Build phase: Dev agent."""
        run_id = str(uuid.uuid4())[:8]
        
        context = AgentContext(
            workspace_path=self.workspace_path,
            run_id=run_id,
            phase=AgentPhase.BUILD,
            inputs={
                "blueprint": blueprint.to_yaml(),
            },
        )
        
        # Run Dev
        dev = self.load_agent(AgentRole.DEV)
        dev_result = await dev.execute(context)
        
        # Save dev traces and conversation
        self._save_traces(run_id, context.traces)
        self._save_conversation(run_id, dev, "dev")
        
        manifest = RunManifest(
            id=run_id,
            blueprint_id=blueprint.id,
            started_at=datetime.utcnow().isoformat(),
            status="completed" if dev_result.success else "failed",
            phase="build",
            agent_results={"dev": dev_result},
            traces=context.traces,
            error=dev_result.error,
        )
        
        manifest.completed_at = datetime.utcnow().isoformat()
        
        # Save manifest to memory
        self.memory.save_memory(
            key=f"manifest_{run_id}",
            value=yaml.dump(manifest.to_dict()),
            metadata={
                "type": "manifest",
                "phase": "build",
                "blueprint_id": blueprint.id,
                "status": manifest.status,
            },
        )
        
        # Save manifest to file
        manifest_path = self.runs_dir / f"{run_id}.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest.to_dict(), f)
        
        return manifest
    
    async def verify(
        self,
        blueprint: Blueprint,
        build_manifest: RunManifest,
    ) -> RunManifest:
        """Execute the Verify phase: QA agent."""
        run_id = str(uuid.uuid4())[:8]
        
        dev_result = build_manifest.agent_results.get("dev")
        
        context = AgentContext(
            workspace_path=self.workspace_path,
            run_id=run_id,
            phase=AgentPhase.VERIFY,
            inputs={
                "blueprint": blueprint.to_yaml(),
                "code_changes": dev_result.outputs.get("code_changes", "") if dev_result else "",
                "acceptance_criteria": blueprint.requirements.get("acceptance_criteria", []),
            },
        )
        
        # Run QA
        qa = self.load_agent(AgentRole.QA)
        qa_result = await qa.execute(context)
        
        # Save QA traces and conversation
        self._save_traces(run_id, context.traces)
        self._save_conversation(run_id, qa, "qa")
        
        manifest = RunManifest(
            id=run_id,
            blueprint_id=blueprint.id,
            started_at=datetime.utcnow().isoformat(),
            status="approved" if qa_result.success else "rejected",
            phase="verify",
            agent_results={"qa": qa_result},
            traces=context.traces,
            error=qa_result.error,
        )
        
        manifest.completed_at = datetime.utcnow().isoformat()
        
        # Save manifest to memory
        self.memory.save_memory(
            key=f"manifest_{run_id}_verify",
            value=yaml.dump(manifest.to_dict()),
            metadata={
                "type": "manifest",
                "phase": "verify",
                "blueprint_id": blueprint.id,
                "build_run_id": build_manifest.id,
                "status": manifest.status,
            },
        )
        
        # Save manifest to file
        manifest_path = self.runs_dir / f"{run_id}.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest.to_dict(), f)
        
        return manifest
    
    async def run(
        self,
        user_request: str,
        context_files: Optional[list[str]] = None,
    ) -> tuple[Blueprint, RunManifest, RunManifest]:
        """Run the full pipeline: Plan → Build → Verify."""
        # Plan phase
        blueprint = await self.plan(user_request, context_files)
        
        # Build phase
        build_manifest = await self.build(blueprint)
        
        # Verify phase
        verify_manifest = await self.verify(blueprint, build_manifest)
        
        return blueprint, build_manifest, verify_manifest
    
    # ==================== Memory Query Methods ====================
    
    def search_past_requests(self, query: str, limit: int = 5) -> list[dict]:
        """Search past user requests using semantic search."""
        return self.memory.search_memories(
            query=query,
            limit=limit,
            metadata_filter={"type": "user_request"},
        )
    
    def search_past_blueprints(self, query: str, limit: int = 5) -> list[dict]:
        """Search past blueprints using semantic search."""
        return self.memory.search_memories(
            query=query,
            limit=limit,
            metadata_filter={"type": "blueprint"},
        )
    
    def get_run_traces(self, run_id: str) -> list[dict]:
        """Get all traces for a specific run."""
        return self.memory.get_traces(run_id)
    
    def get_run_conversation(self, run_id: str, phase: str) -> list[dict]:
        """Get conversation for a specific run and phase."""
        return self.memory.get_conversation(f"{run_id}_{phase}")
    
    def get_memory_stats(self) -> dict:
        """Get memory system statistics."""
        return self.memory.get_stats()
