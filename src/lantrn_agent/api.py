"""FastAPI application for Lantrn Agent Builder.

Provides REST API and WebSocket endpoints for agent execution.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yaml

from .core.config import ConfigManager, init_config
from .core.pipeline import Blueprint, Pipeline, RunManifest
from .models.llm import OllamaAdapter


# Request/Response models
class PlanRequest(BaseModel):
    request: str
    context_files: Optional[list[str]] = None
    profile: str = "fast"


class BuildRequest(BaseModel):
    blueprint_id: str


class RunRequest(BaseModel):
    request: str
    context_files: Optional[list[str]] = None


class BlueprintResponse(BaseModel):
    id: str
    created_at: str
    user_request: str
    requirements: dict[str, Any]
    tasks: list[dict[str, Any]]
    files: list[dict[str, Any]]


class RunResponse(BaseModel):
    id: str
    blueprint_id: str
    status: str
    phase: str
    started_at: str
    completed_at: Optional[str]
    error: Optional[str]


class ModelInfo(BaseModel):
    name: str
    provider: str
    ctx_length: int
    temperature: float


class AgentInfo(BaseModel):
    role: str
    phase: str
    model_profile: str
    tools: list[str]


class StatusResponse(BaseModel):
    status: str
    version: str
    workspace: str
    ollama_connected: bool
    models_count: int
    agents_count: int


def create_app(workspace_path: Path) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="Lantrn Agent Builder",
        description="On-prem deployable AI agent system with BMad v6 Alpha methodology",
        version="0.1.0",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize config
    config = init_config(workspace_path / "config")
    pipeline = Pipeline(workspace_path)
    
    # Store active WebSocket connections
    active_connections: list[WebSocket] = []
    
    @app.get("/", response_model=StatusResponse)
    async def status():
        """Get API status."""
        ollama_connected = False
        models_count = 0
        
        try:
            adapter = OllamaAdapter()
            models = await adapter.list_models()
            ollama_connected = True
            models_count = len(models)
        except:
            pass
        
        agents_count = len(list((workspace_path / "agents").glob("*.bmad.yaml")))
        
        return StatusResponse(
            status="running",
            version="0.1.0",
            workspace=str(workspace_path),
            ollama_connected=ollama_connected,
            models_count=models_count,
            agents_count=agents_count,
        )
    
    @app.get("/models", response_model=list[ModelInfo])
    async def list_models():
        """List available models."""
        models = []
        
        # Get Ollama models
        try:
            adapter = OllamaAdapter()
            ollama_models = await adapter.list_models()
            for name in ollama_models:
                models.append(ModelInfo(
                    name=name,
                    provider="ollama",
                    ctx_length=128000,
                    temperature=0.7,
                ))
        except:
            pass
        
        # Add configured profiles
        for profile_name in config.list_model_profiles():
            profile = config.get_model_profile(profile_name)
            if profile.model not in [m.name for m in models]:
                models.append(ModelInfo(
                    name=profile.model,
                    provider=profile.provider,
                    ctx_length=profile.ctx_length,
                    temperature=profile.temperature,
                ))
        
        return models
    
    @app.get("/agents", response_model=list[AgentInfo])
    async def list_agents():
        """List available agents."""
        agents = []
        agents_dir = workspace_path / "agents"
        
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.bmad.yaml"):
                with open(agent_file) as f:
                    data = yaml.safe_load(f)
                
                role = data.get("role", "unknown")
                phase = "plan" if role in ["analyst", "pm", "architect"] else "build"
                
                agents.append(AgentInfo(
                    role=role,
                    phase=phase,
                    model_profile=data.get("model_profile", "fast"),
                    tools=data.get("tools", []),
                ))
        
        return agents
    
    @app.post("/api/plan", response_model=BlueprintResponse)
    async def create_plan(request: PlanRequest):
        """Run the Plan phase (Analyst → PM → Architect)."""
        try:
            blueprint = await pipeline.plan(request.request, request.context_files)
            
            return BlueprintResponse(
                id=blueprint.id,
                created_at=blueprint.created_at,
                user_request=blueprint.user_request,
                requirements=blueprint.requirements,
                tasks=blueprint.tasks,
                files=blueprint.files,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/plan/{blueprint_id}", response_model=BlueprintResponse)
    async def get_blueprint(blueprint_id: str):
        """Get a blueprint by ID."""
        blueprint_path = workspace_path / ".bmad" / "blueprints" / f"{blueprint_id}.yaml"
        
        if not blueprint_path.exists():
            raise HTTPException(status_code=404, detail="Blueprint not found")
        
        with open(blueprint_path) as f:
            data = yaml.safe_load(f)
        
        return BlueprintResponse(
            id=data["id"],
            created_at=data["created_at"],
            user_request=data["user_request"],
            requirements=data["requirements"],
            tasks=data["tasks"],
            files=data["files"],
        )
    
    @app.post("/api/build/{blueprint_id}", response_model=RunResponse)
    async def create_build(blueprint_id: str):
        """Run the Build phase (Dev agent)."""
        blueprint_path = workspace_path / ".bmad" / "blueprints" / f"{blueprint_id}.yaml"
        
        if not blueprint_path.exists():
            raise HTTPException(status_code=404, detail="Blueprint not found")
        
        with open(blueprint_path) as f:
            data = yaml.safe_load(f)
        
        blueprint = Blueprint(**data)
        
        try:
            manifest = await pipeline.build(blueprint)
            
            return RunResponse(
                id=manifest.id,
                blueprint_id=manifest.blueprint_id,
                status=manifest.status,
                phase=manifest.phase,
                started_at=manifest.started_at,
                completed_at=manifest.completed_at,
                error=manifest.error,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/run/{run_id}", response_model=RunResponse)
    async def get_run(run_id: str):
        """Get a run by ID."""
        run_path = workspace_path / ".bmad" / "runs" / f"{run_id}.yaml"
        
        if not run_path.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        
        with open(run_path) as f:
            data = yaml.safe_load(f)
        
        return RunResponse(
            id=data["id"],
            blueprint_id=data["blueprint_id"],
            status=data["status"],
            phase=data["phase"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            error=data.get("error"),
        )
    
    @app.post("/api/run", response_model=dict)
    async def run_full_pipeline(request: RunRequest):
        """Run the full pipeline (Plan → Build → Verify)."""
        try:
            blueprint, build_manifest, verify_manifest = await pipeline.run(
                request.request,
                request.context_files,
            )
            
            return {
                "blueprint_id": blueprint.id,
                "build_run_id": build_manifest.id,
                "verify_run_id": verify_manifest.id,
                "build_status": build_manifest.status,
                "verify_status": verify_manifest.status,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/run/{run_id}/trace")
    async def get_run_trace(run_id: str):
        """Get execution trace for a run."""
        run_path = workspace_path / ".bmad" / "runs" / f"{run_id}.yaml"
        
        if not run_path.exists():
            raise HTTPException(status_code=404, detail="Run not found")
        
        with open(run_path) as f:
            data = yaml.safe_load(f)
        
        return {"traces": data.get("traces", [])}
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates."""
        await websocket.accept()
        active_connections.append(websocket)
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "run":
                    # Run pipeline with real-time updates
                    request = data.get("request", "")
                    
                    await websocket.send_json({
                        "type": "status",
                        "phase": "plan",
                        "message": "Starting Plan phase...",
                    })
                    
                    try:
                        blueprint = await pipeline.plan(request)
                        
                        await websocket.send_json({
                            "type": "status",
                            "phase": "build",
                            "message": f"Blueprint {blueprint.id} created. Starting Build phase...",
                        })
                        
                        build_manifest = await pipeline.build(blueprint)
                        
                        await websocket.send_json({
                            "type": "status",
                            "phase": "verify",
                            "message": f"Build {build_manifest.status}. Starting Verify phase...",
                        })
                        
                        verify_manifest = await pipeline.verify(blueprint, build_manifest)
                        
                        await websocket.send_json({
                            "type": "complete",
                            "blueprint_id": blueprint.id,
                            "build_status": build_manifest.status,
                            "verify_status": verify_manifest.status,
                        })
                    
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                        })
                
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
        
        except WebSocketDisconnect:
            active_connections.remove(websocket)
    
    return app
