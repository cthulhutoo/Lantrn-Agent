"""Workspace manager for Lantrn Agent Builder.

Orchestrates workspace isolation, manifest tracking, and diff tracking.
"""

import asyncio
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import uuid

from lantrn_agent.workspace.isolation import IsolationContext, IsolationConfig, MultiServiceSupport
from lantrn_agent.workspace.manifest import RunManifest, ManifestStore, RunStep
from lantrn_agent.workspace.diff_tracker import DiffTracker, ChangeSet


@dataclass
class WorkspaceConfig:
    """Configuration for workspace management."""
    
    root: Path = field(default_factory=lambda: Path("./workspaces"))
    max_workspaces: int = 10
    auto_cleanup: bool = True
    preserve_successful_runs: bool = False
    preserve_failed_runs: bool = True
    snapshot_on_start: bool = True
    snapshot_on_complete: bool = True
    
    def __post_init__(self):
        self.root = Path(self.root)


class WorkspaceManager:
    """Manages workspaces for agent execution.
    
    Provides:
    - Workspace creation and isolation
    - Run manifest tracking
    - Change tracking and diffs
    - Multi-service support
    - Cleanup and archival
    """
    
    def __init__(self, config: Optional[WorkspaceConfig] = None):
        self.config = config or WorkspaceConfig()
        self.config.root.mkdir(parents=True, exist_ok=True)
        
        self._active_workspaces: dict[str, IsolationContext] = {}
        self._manifest_stores: dict[str, ManifestStore] = {}
        self._diff_trackers: dict[str, DiffTracker] = {}
        self._multi_service = MultiServiceSupport(self.config.root)
    
    def create_workspace(
        self,
        name: Optional[str] = None,
        isolation_config: Optional[IsolationConfig] = None,
    ) -> tuple[str, IsolationContext]:
        """Create a new workspace.
        
        Args:
            name: Optional workspace name
            isolation_config: Optional isolation config
            
        Returns:
            Tuple of (workspace_id, IsolationContext)
        """
        workspace_id = name or f"ws_{uuid.uuid4().hex[:8]}"
        workspace_root = self.config.root / workspace_id
        
        context = IsolationContext(
            id=workspace_id,
            root=workspace_root,
            config=isolation_config or IsolationConfig(
                preserve_on_exit=not self.config.auto_cleanup,
            ),
        )
        context.setup()
        
        self._active_workspaces[workspace_id] = context
        self._manifest_stores[workspace_id] = ManifestStore(workspace_root)
        self._diff_trackers[workspace_id] = DiffTracker(workspace_root / "workspace")
        
        return workspace_id, context
    
    def get_workspace(self, workspace_id: str) -> Optional[IsolationContext]:
        """Get an existing workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            IsolationContext or None
        """
        return self._active_workspaces.get(workspace_id)
    
    def get_manifest_store(self, workspace_id: str) -> Optional[ManifestStore]:
        """Get manifest store for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            ManifestStore or None
        """
        return self._manifest_stores.get(workspace_id)
    
    def get_diff_tracker(self, workspace_id: str) -> Optional[DiffTracker]:
        """Get diff tracker for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
            Returns:
            DiffTracker or None
        """
        return self._diff_trackers.get(workspace_id)
    
    def list_workspaces(self) -> list[dict]:
        """List all workspaces.
        
        Returns:
            List of workspace info dicts
        """
        workspaces = []
        for ws_id, context in self._active_workspaces.items():
            workspaces.append({
                "id": ws_id,
                "root": str(context.root),
                "created": context.root.stat().st_ctime if context.root.exists() else None,
            })
        return workspaces
    
    async def start_run(
        self,
        workspace_id: str,
        name: str,
        description: str = "",
        pipeline_type: str = "plan_build_verify",
    ) -> Optional[RunManifest]:
        """Start a new run in a workspace.
        
        Args:
            workspace_id: Workspace ID
            name: Run name
            description: Run description
            pipeline_type: Pipeline type
            
        Returns:
            RunManifest or None
        """
        store = self._manifest_stores.get(workspace_id)
        tracker = self._diff_trackers.get(workspace_id)
        
        if not store:
            return None
        
        manifest = RunManifest(
            name=name,
            description=description,
            pipeline_type=pipeline_type,
        )
        manifest.start()
        store.save(manifest)
        
        # Capture initial snapshot if configured
        if tracker and self.config.snapshot_on_start:
            files = await tracker.scan_workspace()
            await tracker.capture_before(files)
        
        return manifest
    
    async def complete_run(
        self,
        workspace_id: str,
        manifest: RunManifest,
        success: bool = True,
        error: Optional[str] = None,
    ) -> Optional[ChangeSet]:
        """Complete a run.
        
        Args:
            workspace_id: Workspace ID
            manifest: Run manifest
            success: Whether run succeeded
            error: Error message if failed
            
        Returns:
            ChangeSet or None
        """
        store = self._manifest_stores.get(workspace_id)
        tracker = self._diff_trackers.get(workspace_id)
        
        if success:
            manifest.complete()
        else:
            manifest.fail(error or "Unknown error")
        
        if store:
            store.save(manifest)
        
        # Capture final snapshot and compute changes
        change_set = None
        if tracker and self.config.snapshot_on_complete:
            files = await tracker.scan_workspace()
            await tracker.capture_after(files)
            change_set = await tracker.compute_change_set(
                description=f"Changes from run {manifest.id}"
            )
            
            # Save change set
            changes_path = self._active_workspaces[workspace_id].root / "changes" / f"{manifest.id}.json"
            await tracker.save_change_set(change_set, changes_path)
        
        return change_set
    
    def cleanup_workspace(self, workspace_id: str) -> bool:
        """Clean up a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            True if cleaned up
        """
        context = self._active_workspaces.get(workspace_id)
        if context:
            context.cleanup()
            del self._active_workspaces[workspace_id]
            self._manifest_stores.pop(workspace_id, None)
            self._diff_trackers.pop(workspace_id, None)
            return True
        return False
    
    def cleanup_all(self) -> int:
        """Clean up all workspaces.
        
        Returns:
            Number of workspaces cleaned
        """
        count = 0
        for ws_id in list(self._active_workspaces.keys()):
            if self.cleanup_workspace(ws_id):
                count += 1
        return count
    
    def archive_workspace(self, workspace_id: str, archive_path: Path) -> bool:
        """Archive a workspace to a tarball.
        
        Args:
            workspace_id: Workspace ID
            archive_path: Path for archive
            
        Returns:
            True if archived
        """
        context = self._active_workspaces.get(workspace_id)
        if not context or not context.root.exists():
            return False
        
        archive_path = Path(archive_path)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.make_archive(
            str(archive_path.with_suffix('')),
            'gztar',
            context.root,
        )
        return True
    
    def get_run_history(
        self,
        workspace_id: str,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> list[RunManifest]:
        """Get run history for a workspace.
        
        Args:
            workspace_id: Workspace ID
            limit: Maximum runs to return
            status: Optional status filter
            
        Returns:
            List of RunManifest objects
        """
        store = self._manifest_stores.get(workspace_id)
        if not store:
            return []
        return store.list_runs(status=status, limit=limit)
    
    def get_workspace_stats(self, workspace_id: str) -> dict:
        """Get statistics for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            Statistics dict
        """
        context = self._active_workspaces.get(workspace_id)
        store = self._manifest_stores.get(workspace_id)
        
        if not context:
            return {}
        
        runs = store.list_runs() if store else []
        
        return {
            "id": workspace_id,
            "root": str(context.root),
            "total_runs": len(runs),
            "successful_runs": sum(1 for r in runs if r.status == "completed"),
            "failed_runs": sum(1 for r in runs if r.status == "failed"),
            "total_tokens": sum(r.total_tokens for r in runs),
            "total_cost": sum(r.total_cost for r in runs),
        }


# Context partitioning support
class ContextPartition:
    """Partition for context isolation within a workspace."""
    
    def __init__(self, workspace_id: str, partition_id: str, root: Path):
        self.workspace_id = workspace_id
        self.partition_id = partition_id
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
    
    @property
    def data_path(self) -> Path:
        return self.root / "data"
    
    @property
    def cache_path(self) -> Path:
        return self.root / "cache"
    
    @property
    def logs_path(self) -> Path:
        return self.root / "logs"
    
    def setup(self) -> None:
        """Set up partition directories."""
        for path in [self.data_path, self.cache_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)


class PartitionManager:
    """Manages context partitions within workspaces."""
    
    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace_manager = workspace_manager
        self._partitions: dict[str, ContextPartition] = {}
    
    def create_partition(
        self,
        workspace_id: str,
        partition_id: str,
    ) -> Optional[ContextPartition]:
        """Create a context partition.
        
        Args:
            workspace_id: Workspace ID
            partition_id: Partition ID
            
        Returns:
            ContextPartition or None
        """
        context = self.workspace_manager.get_workspace(workspace_id)
        if not context:
            return None
        
        partition = ContextPartition(
            workspace_id=workspace_id,
            partition_id=partition_id,
            root=context.root / "partitions" / partition_id,
        )
        partition.setup()
        
        key = f"{workspace_id}:{partition_id}"
        self._partitions[key] = partition
        return partition
    
    def get_partition(
        self,
        workspace_id: str,
        partition_id: str,
    ) -> Optional[ContextPartition]:
        """Get a context partition.
        
        Args:
            workspace_id: Workspace ID
            partition_id: Partition ID
            
        Returns:
            ContextPartition or None
        """
        return self._partitions.get(f"{workspace_id}:{partition_id}")
    
    def list_partitions(self, workspace_id: str) -> list[str]:
        """List partitions for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            List of partition IDs
        """
        return [
            pid.split(":")[1]
            for pid in self._partitions
            if pid.startswith(f"{workspace_id}:")
        ]
