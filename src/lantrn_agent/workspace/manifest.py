"""Run manifest for Lantrn Agent Builder.

Tracks execution runs, their status, and results.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import uuid


@dataclass
class RunStep:
    """A single step in a run."""
    
    name: str
    agent: str
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    error: Optional[str] = None
    
    def start(self) -> None:
        """Mark step as started."""
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()
    
    def complete(self, output: dict = None) -> None:
        """Mark step as completed."""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        if output:
            self.output_data = output
    
    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.status = "failed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.error = error


@dataclass
class RunManifest:
    """Manifest for tracking a single agent execution run.
    
    Provides:
    - Run identification and metadata
    - Step-by-step execution tracking
    - Input/output artifact tracking
    - Timing and status information
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: str = "pending"  # pending, running, completed, failed, cancelled
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Pipeline info
    pipeline_type: str = "plan_build_verify"  # or "single_agent", "custom"
    current_phase: str = ""  # plan, build, verify
    current_step: int = 0
    
    # Steps
    steps: list[RunStep] = field(default_factory=list)
    
    # Artifacts
    input_artifacts: dict[str, str] = field(default_factory=dict)  # name -> path
    output_artifacts: dict[str, str] = field(default_factory=dict)  # name -> path
    
    # Configuration
    config: dict = field(default_factory=dict)
    model_profile: str = "fast"
    
    # Metrics
    total_tokens: int = 0
    total_cost: float = 0.0
    
    # Error tracking
    error: Optional[str] = None
    retry_count: int = 0
    
    def __post_init__(self):
        # Convert step dicts to RunStep objects if needed
        if self.steps and isinstance(self.steps[0], dict):
            self.steps = [RunStep(**s) if isinstance(s, dict) else s for s in self.steps]
    
    def start(self) -> None:
        """Mark run as started."""
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()
    
    def complete(self) -> None:
        """Mark run as completed."""
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
    
    def fail(self, error: str) -> None:
        """Mark run as failed."""
        self.status = "failed"
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.error = error
    
    def cancel(self) -> None:
        """Mark run as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.now(timezone.utc).isoformat()
    
    def add_step(self, name: str, agent: str, input_data: dict = None) -> RunStep:
        """Add a step to the run.
        
        Args:
            name: Step name
            agent: Agent name
            input_data: Optional input data
            
        Returns:
            The created RunStep
        """
        step = RunStep(
            name=name,
            agent=agent,
            input_data=input_data or {},
        )
        self.steps.append(step)
        return step
    
    def get_current_step(self) -> Optional[RunStep]:
        """Get the current step.
        
        Returns:
            Current RunStep or None
        """
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def advance_step(self) -> Optional[RunStep]:
        """Advance to the next step.
        
        Returns:
            Next RunStep or None if complete
        """
        self.current_step += 1
        return self.get_current_step()
    
    def add_input_artifact(self, name: str, path: str) -> None:
        """Add an input artifact.
        
        Args:
            name: Artifact name
            path: Path to artifact
        """
        self.input_artifacts[name] = path
    
    def add_output_artifact(self, name: str, path: str) -> None:
        """Add an output artifact.
        
        Args:
            name: Artifact name
            path: Path to artifact
        """
        self.output_artifacts[name] = path
    
    def update_metrics(self, tokens: int, cost: float) -> None:
        """Update run metrics.
        
        Args:
            tokens: Tokens used
            cost: Cost in dollars
        """
        self.total_tokens += tokens
        self.total_cost += cost
    
    def to_dict(self) -> dict:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        data = asdict(self)
        # Ensure steps are properly serialized
        data["steps"] = [asdict(s) if hasattr(s, '__dataclass_fields__') else s for s in self.steps]
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> "RunManifest":
        """Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            RunManifest instance
        """
        # Handle steps conversion
        if "steps" in data:
            data["steps"] = [RunStep(**s) if isinstance(s, dict) else s for s in data["steps"]]
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "RunManifest":
        """Create from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            RunManifest instance
        """
        return cls.from_dict(json.loads(json_str))
    
    def save(self, path: Path) -> None:
        """Save manifest to file.
        
        Args:
            path: Path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
    
    @classmethod
    def load(cls, path: Path) -> "RunManifest":
        """Load manifest from file.
        
        Args:
            path: Path to load from
            
        Returns:
            RunManifest instance
        """
        path = Path(path)
        return cls.from_json(path.read_text())
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get run duration in seconds.
        
        Returns:
            Duration in seconds or None if not complete
        """
        if not self.started_at:
            return None
        
        end = self.completed_at or datetime.now(timezone.utc).isoformat()
        start = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        return (end_dt - start).total_seconds()
    
    def get_summary(self) -> dict:
        """Get a summary of the run.
        
        Returns:
            Summary dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "duration_seconds": self.get_duration_seconds(),
            "steps_completed": sum(1 for s in self.steps if s.status == "completed"),
            "steps_total": len(self.steps),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "error": self.error,
        }


class ManifestStore:
    """Store for managing multiple run manifests."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.manifests_dir = self.base_dir / "manifests"
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, manifest: RunManifest) -> Path:
        """Save a manifest.
        
        Args:
            manifest: Manifest to save
            
        Returns:
            Path to saved manifest
        """
        path = self.manifests_dir / f"{manifest.id}.json"
        manifest.save(path)
        return path
    
    def load(self, run_id: str) -> Optional[RunManifest]:
        """Load a manifest by ID.
        
        Args:
            run_id: Run ID
            
        Returns:
            RunManifest or None
        """
        path = self.manifests_dir / f"{run_id}.json"
        if path.exists():
            return RunManifest.load(path)
        return None
    
    def list_runs(self, status: Optional[str] = None, limit: int = 100) -> list[RunManifest]:
        """List runs, optionally filtered by status.
        
        Args:
            status: Optional status filter
            limit: Maximum number to return
            
        Returns:
            List of RunManifest objects
        """
        runs = []
        for path in sorted(self.manifests_dir.glob("*.json"), reverse=True)[:limit]:
            manifest = RunManifest.load(path)
            if status is None or manifest.status == status:
                runs.append(manifest)
        return runs
    
    def delete(self, run_id: str) -> bool:
        """Delete a manifest.
        
        Args:
            run_id: Run ID
            
        Returns:
            True if deleted
        """
        path = self.manifests_dir / f"{run_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
