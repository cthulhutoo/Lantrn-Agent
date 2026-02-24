"""Base classes for BMad agents.

Implements the role chain: Analyst → PM → Architect → Dev → QA
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import yaml

from ..models.llm import Message, MessageRole, ChatResponse, get_llm_adapter
from ..core.config import get_config, ModelProfile


class AgentRole(str, Enum):
    """BMad agent roles."""
    ANALYST = "analyst"
    PM = "pm"
    ARCHITECT = "architect"
    DEV = "dev"
    QA = "qa"


class AgentPhase(str, Enum):
    """BMad phases."""
    PLAN = "plan"
    BUILD = "build"
    VERIFY = "verify"


@dataclass
class AgentDefinition:
    """Definition of an agent from YAML file."""
    role: str
    version: str = "1.0"
    objective: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    model_profile: str = "fast"
    prompt_template: str = ""
    success_criteria: list[str] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "AgentDefinition":
        """Load agent definition from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(
            role=data.get("role", "unknown"),
            version=data.get("version", "1.0"),
            objective=data.get("objective", ""),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            tools=data.get("tools", []),
            model_profile=data.get("model_profile", "fast"),
            prompt_template=data.get("prompt_template", ""),
            success_criteria=data.get("success_criteria", []),
        )


@dataclass
class AgentContext:
    """Context for agent execution."""
    workspace_path: Path
    run_id: str
    phase: AgentPhase
    inputs: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    traces: list[dict] = field(default_factory=list)
    
    def add_trace(self, action: str, details: dict[str, Any]) -> None:
        """Add a trace entry."""
        self.traces.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details,
        })


@dataclass
class AgentResult:
    """Result of agent execution."""
    success: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    traces: list[dict] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = 0.0


class BaseAgent(ABC):
    """Base class for all BMad agents."""
    
    role: AgentRole = None  # type: ignore
    phase: AgentPhase = None  # type: ignore
    
    def __init__(
        self,
        definition: AgentDefinition,
        model_profile: Optional[ModelProfile] = None,
    ):
        self.definition = definition
        self.config = get_config()
        self.model_profile = model_profile or self.config.get_model_profile(definition.model_profile)
        self.llm = get_llm_adapter(
            provider=self.model_profile.provider,
            base_url=self.model_profile.api_base,
        )
        self.conversation_history: list[Message] = []
    
    @classmethod
    def from_yaml(cls, path: Path) -> "BaseAgent":
        """Create agent from YAML definition file."""
        definition = AgentDefinition.from_yaml(path)
        
        # Map role to agent class
        role_to_class = {
            AgentRole.ANALYST: AnalystAgent,
            AgentRole.PM: PMAgent,
            AgentRole.ARCHITECT: ArchitectAgent,
            AgentRole.DEV: DevAgent,
            AgentRole.QA: QAAgent,
        }
        
        agent_class = role_to_class.get(AgentRole(definition.role))
        if not agent_class:
            raise ValueError(f"Unknown agent role: {definition.role}")
        
        return agent_class(definition)
    
    def system_prompt(self) -> str:
        """Generate system prompt from definition."""
        return self.definition.prompt_template or f"""You are the {self.definition.role} agent in the BMad methodology.

Objective: {self.definition.objective}

Inputs: {', '.join(self.definition.inputs)}
Outputs: {', '.join(self.definition.outputs)}

Success Criteria:
{chr(10).join(f'- {c}' for c in self.definition.success_criteria)}
"""
    
    async def chat(
        self,
        message: str,
        include_history: bool = True,
    ) -> ChatResponse:
        """Send a message to the LLM."""
        messages = []
        
        # Add system prompt
        if not self.conversation_history:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=self.system_prompt(),
            ))
        
        # Add conversation history
        if include_history:
            messages.extend(self.conversation_history)
        
        # Add new message
        user_message = Message(role=MessageRole.USER, content=message)
        messages.append(user_message)
        
        # Get response
        response = await self.llm.chat(
            messages=messages,
            model=self.model_profile.model,
            temperature=self.model_profile.temperature,
        )
        
        # Update history
        self.conversation_history.append(user_message)
        self.conversation_history.append(Message(
            role=MessageRole.ASSISTANT,
            content=response.content,
        ))
        
        return response
    
    async def chat_stream(self, message: str, include_history: bool = True):
        """Stream a response from the LLM."""
        messages = []
        
        if not self.conversation_history:
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=self.system_prompt(),
            ))
        
        if include_history:
            messages.extend(self.conversation_history)
        
        user_message = Message(role=MessageRole.USER, content=message)
        messages.append(user_message)
        
        full_response = ""
        async for chunk in self.llm.chat_stream(
            messages=messages,
            model=self.model_profile.model,
            temperature=self.model_profile.temperature,
        ):
            full_response += chunk
            yield chunk
        
        self.conversation_history.append(user_message)
        self.conversation_history.append(Message(
            role=MessageRole.ASSISTANT,
            content=full_response,
        ))
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's task."""
        pass
    
    def reset(self) -> None:
        """Reset conversation history."""
        self.conversation_history = []


class AnalystAgent(BaseAgent):
    """Analyst agent - First role in Plan phase."""
    
    role = AgentRole.ANALYST
    phase = AgentPhase.PLAN
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Analyze requirements and produce requirements document."""
        context.add_trace("analyst_start", {"inputs": context.inputs})
        
        try:
            # Build analysis prompt
            user_request = context.inputs.get("user_request", "")
            context_files = context.inputs.get("context_files", [])
            
            prompt = f"""Analyze the following request and produce a requirements document.

User Request:
{user_request}

Context Files:
{chr(10).join(context_files) if context_files else 'None provided'}

Please provide:
1. Requirements Document
2. Constraints
3. Success Criteria
4. Clarifying Questions (if any)
"""
            
            response = await self.chat(prompt)
            
            outputs = {
                "requirements_doc": response.content,
                "constraints": [],
                "success_criteria": [],
                "clarifying_questions": [],
            }
            
            context.add_trace("analyst_complete", {"outputs": outputs})
            
            return AgentResult(
                success=True,
                outputs=outputs,
                traces=context.traces,
            )
        
        except Exception as e:
            context.add_trace("analyst_error", {"error": str(e)})
            return AgentResult(
                success=False,
                error=str(e),
                traces=context.traces,
            )


class PMAgent(BaseAgent):
    """PM agent - Second role in Plan phase."""
    
    role = AgentRole.PM
    phase = AgentPhase.PLAN
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Transform requirements into tasks."""
        context.add_trace("pm_start", {"inputs": context.inputs})
        
        try:
            requirements = context.inputs.get("requirements_doc", "")
            
            prompt = f"""Transform the following requirements into actionable tasks.

Requirements:
{requirements}

Please provide:
1. Task List (with IDs and descriptions)
2. Acceptance Criteria for each task
3. Priority Order
4. Dependencies between tasks
"""
            
            response = await self.chat(prompt)
            
            outputs = {
                "task_list": response.content,
                "acceptance_criteria": [],
                "priority_order": [],
                "dependencies": [],
            }
            
            context.add_trace("pm_complete", {"outputs": outputs})
            
            return AgentResult(
                success=True,
                outputs=outputs,
                traces=context.traces,
            )
        
        except Exception as e:
            context.add_trace("pm_error", {"error": str(e)})
            return AgentResult(
                success=False,
                error=str(e),
                traces=context.traces,
            )


class ArchitectAgent(BaseAgent):
    """Architect agent - Third role in Plan phase."""
    
    role = AgentRole.ARCHITECT
    phase = AgentPhase.PLAN
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Design solution and produce Blueprint."""
        context.add_trace("architect_start", {"inputs": context.inputs})
        
        try:
            task_list = context.inputs.get("task_list", "")
            
            prompt = f"""Design the technical solution for the following tasks.

Tasks:
{task_list}

Please provide:
1. Blueprint (YAML format)
2. File Specifications
3. Tool Budgets
4. Architecture Decisions
"""
            
            response = await self.chat(prompt)
            
            outputs = {
                "blueprint": response.content,
                "file_specifications": [],
                "tool_budgets": {},
                "architecture_decisions": [],
            }
            
            context.add_trace("architect_complete", {"outputs": outputs})
            
            return AgentResult(
                success=True,
                outputs=outputs,
                traces=context.traces,
            )
        
        except Exception as e:
            context.add_trace("architect_error", {"error": str(e)})
            return AgentResult(
                success=False,
                error=str(e),
                traces=context.traces,
            )


class DevAgent(BaseAgent):
    """Dev agent - First role in Build phase."""
    
    role = AgentRole.DEV
    phase = AgentPhase.BUILD
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute Blueprint and write code."""
        context.add_trace("dev_start", {"inputs": context.inputs})
        
        try:
            blueprint = context.inputs.get("blueprint", "")
            
            prompt = f"""Execute the following Blueprint and produce code changes.

Blueprint:
{blueprint}

Please provide:
1. Code Changes (file by file)
2. Execution Log
3. Any issues encountered
"""
            
            response = await self.chat(prompt)
            
            outputs = {
                "code_changes": response.content,
                "execution_log": [],
                "issues": [],
            }
            
            context.add_trace("dev_complete", {"outputs": outputs})
            
            return AgentResult(
                success=True,
                outputs=outputs,
                traces=context.traces,
            )
        
        except Exception as e:
            context.add_trace("dev_error", {"error": str(e)})
            return AgentResult(
                success=False,
                error=str(e),
                traces=context.traces,
            )


class QAAgent(BaseAgent):
    """QA agent - Second role in Build phase."""
    
    role = AgentRole.QA
    phase = AgentPhase.VERIFY
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Verify Dev work against acceptance criteria."""
        context.add_trace("qa_start", {"inputs": context.inputs})
        
        try:
            blueprint = context.inputs.get("blueprint", "")
            code_changes = context.inputs.get("code_changes", "")
            acceptance_criteria = context.inputs.get("acceptance_criteria", "")
            
            prompt = f"""Verify the following code changes against the Blueprint and acceptance criteria.

Blueprint:
{blueprint}

Code Changes:
{code_changes}

Acceptance Criteria:
{acceptance_criteria}

Please provide:
1. Verification Report
2. Test Results
3. Issues Found
4. Approval Status (approved/rejected)
"""
            
            response = await self.chat(prompt)
            
            outputs = {
                "verification_report": response.content,
                "test_results": [],
                "issues_found": [],
                "approval_status": "pending",
            }
            
            context.add_trace("qa_complete", {"outputs": outputs})
            
            return AgentResult(
                success=True,
                outputs=outputs,
                traces=context.traces,
            )
        
        except Exception as e:
            context.add_trace("qa_error", {"error": str(e)})
            return AgentResult(
                success=False,
                error=str(e),
                traces=context.traces,
            )
