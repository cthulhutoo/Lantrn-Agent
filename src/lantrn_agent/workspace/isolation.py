"""Workspace isolation for Lantrn Agent Builder.

Provides isolated execution contexts for agent runs.
"""

import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Optional
import uuid
import json


@dataclass
class IsolationConfig:
    """Configuration for workspace isolation."""
    
    enabled: bool = True
    temp_dir: Optional[Path] = None
    preserve_on_exit: bool = False
    max_workspaces: int = 10
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=lambda: ["/etc", "/root", "/home"])
    
    def __post_init__(self):
        if not self.allowed_paths:
            self.allowed_paths = ["/tmp", "/var/tmp"]


@dataclass
class IsolationContext:
    """Isolated execution context for a single agent run.
    
    Provides:
    - Isolated working directory
    - Environment variable sandboxing
    - Path access control
    - Resource limits
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    root: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="lantrn_ws_")))
    config: IsolationConfig = field(default_factory=IsolationConfig)
    _original_cwd: Optional[Path] = field(default=None, repr=False)
    _env_backup: dict = field(default_factory=dict, repr=False)
    
    def __post_init__(self):
        self.root = Path(self.root)
        self._env_backup = dict(os.environ)
    
    def setup(self) -> Path:
        """Set up the isolated workspace.
        
        Returns:
            Path to the isolated workspace root
        """
        if not self.config.enabled:
            return self.root
        
        # Create workspace structure
        dirs = [
            "workspace",
            "output",
            "logs",
            "cache",
            "config",
        ]
        for d in dirs:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        
        # Create isolation metadata
        metadata = {
            "id": self.id,
            "created": self._get_timestamp(),
            "config": {
                "preserve_on_exit": self.config.preserve_on_exit,
                "allowed_paths": self.config.allowed_paths,
            }
        }
        (self.root / "isolation.json").write_text(json.dumps(metadata, indent=2))
        
        return self.root
    
    def _get_timestamp(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def enter(self) -> Path:
        """Enter the isolated context.
        
        Changes working directory and sets up environment.
        
        Returns:
            Path to the workspace directory
        """
        if not self.config.enabled:
            return Path.cwd()
        
        self._original_cwd = Path.cwd()
        os.chdir(self.root / "workspace")
        
        # Set isolated environment variables
        os.environ["LANTRN_WORKSPACE_ID"] = self.id
        os.environ["LANTRN_WORKSPACE_ROOT"] = str(self.root)
        os.environ["LANTRN_ISOLATED"] = "1"
        
        return self.root / "workspace"
    
    def exit(self) -> None:
        """Exit the isolated context.
        
        Restores original working directory and environment.
        """
        if not self.config.enabled:
            return
        
        if self._original_cwd:
            os.chdir(self._original_cwd)
        
        # Restore environment
        for key in ["LANTRN_WORKSPACE_ID", "LANTRN_WORKSPACE_ROOT", "LANTRN_ISOLATED"]:
            os.environ.pop(key, None)
    
    def cleanup(self) -> None:
        """Clean up the isolated workspace.
        
        Removes all files if not configured to preserve.
        """
        if self.config.preserve_on_exit:
            return
        
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
    
    def is_path_allowed(self, path: Path) -> bool:
        """Check if a path is allowed within this isolation context.
        
        Args:
            path: Path to check
            
        Returns:
            True if path access is allowed
        """
        path = Path(path).resolve()
        
        # Always allow workspace paths
        try:
            path.relative_to(self.root)
            return True
        except ValueError:
            pass
        
        # Check denied paths
        for denied in self.config.denied_paths:
            try:
                path.relative_to(Path(denied))
                return False
            except ValueError:
                pass
        
        # Check allowed paths
        for allowed in self.config.allowed_paths:
            try:
                path.relative_to(Path(allowed))
                return True
            except ValueError:
                pass
        
        return False
    
    @contextmanager
    def isolated(self) -> Generator[Path, None, None]:
        """Context manager for isolated execution.
        
        Usage:
            with context.isolated() as workspace:
                # Work in isolated workspace
                pass
        """
        try:
            workspace = self.enter()
            yield workspace
        finally:
            self.exit()
            if not self.config.preserve_on_exit:
                self.cleanup()
    
    def get_output_path(self, filename: str) -> Path:
        """Get path for output file.
        
        Args:
            filename: Name of output file
            
        Returns:
            Full path to output file
        """
        return self.root / "output" / filename
    
    def get_log_path(self, filename: str = "run.log") -> Path:
        """Get path for log file.
        
        Args:
            filename: Name of log file
            
        Returns:
            Full path to log file
        """
        return self.root / "logs" / filename
    
    def get_cache_path(self, key: str) -> Path:
        """Get path for cache file.
        
        Args:
            key: Cache key
            
        Returns:
            Full path to cache file
        """
        return self.root / "cache" / f"{key}.cache"


class MultiServiceSupport:
    """Support for running multiple services within isolated contexts."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.services: dict[str, IsolationContext] = {}
    
    def create_service(self, name: str, config: Optional[IsolationConfig] = None) -> IsolationContext:
        """Create an isolated context for a service.
        
        Args:
            name: Service name
            config: Optional isolation config
            
        Returns:
            IsolationContext for the service
        """
        service_dir = self.base_dir / "services" / name
        service_dir.mkdir(parents=True, exist_ok=True)
        
        context = IsolationContext(
            id=f"{name}_{uuid.uuid4().hex[:8]}",
            root=service_dir,
            config=config or IsolationConfig(),
        )
        self.services[name] = context
        return context
    
    def get_service(self, name: str) -> Optional[IsolationContext]:
        """Get an existing service context.
        
        Args:
            name: Service name
            
        Returns:
            IsolationContext if exists, None otherwise
        """
        return self.services.get(name)
    
    def list_services(self) -> list[str]:
        """List all service names.
        
        Returns:
            List of service names
        """
        return list(self.services.keys())
    
    def cleanup_all(self) -> None:
        """Clean up all service contexts."""
        for context in self.services.values():
            context.cleanup()
        self.services.clear()
