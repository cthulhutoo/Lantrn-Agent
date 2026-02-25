"""Diff and change tracking for Lantrn Agent Builder.

Tracks file changes during agent execution.
"""

import difflib
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import aiofiles


async def _read_file(path: Path) -> str:
    """Read file content asynchronously."""
    async with aiofiles.open(path, 'r') as f:
        return await f.read()


@dataclass
class FileSnapshot:
    """Snapshot of a file at a point in time."""
    
    path: str
    content_hash: str
    size: int
    modified_at: str
    exists: bool = True
    
    @classmethod
    async def capture(cls, path: Path) -> "FileSnapshot":
        """Capture a snapshot of a file.
        
        Args:
            path: Path to file
            
        Returns:
            FileSnapshot
        """
        path = Path(path)
        if not path.exists():
            return cls(
                path=str(path),
                content_hash="",
                size=0,
                modified_at=datetime.now(timezone.utc).isoformat(),
                exists=False,
            )
        
        stat = path.stat()
        content = await _read_file(path)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        return cls(
            path=str(path),
            content_hash=content_hash,
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            exists=True,
        )


@dataclass
class FileDiff:
    """Diff between two file snapshots."""
    
    path: str
    old_snapshot: Optional[FileSnapshot]
    new_snapshot: Optional[FileSnapshot]
    change_type: str  # created, modified, deleted, unchanged
    diff_lines: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "change_type": self.change_type,
            "old_hash": self.old_snapshot.content_hash if self.old_snapshot else None,
            "new_hash": self.new_snapshot.content_hash if self.new_snapshot else None,
            "diff_lines": self.diff_lines,
        }


@dataclass
class ChangeSet:
    """Set of changes between two points in time."""
    
    id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    description: str = ""
    diffs: list[FileDiff] = field(default_factory=list)
    
    @property
    def files_created(self) -> list[str]:
        """List of created files."""
        return [d.path for d in self.diffs if d.change_type == "created"]
    
    @property
    def files_modified(self) -> list[str]:
        """List of modified files."""
        return [d.path for d in self.diffs if d.change_type == "modified"]
    
    @property
    def files_deleted(self) -> list[str]:
        """List of deleted files."""
        return [d.path for d in self.diffs if d.change_type == "deleted"]
    
    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return any(d.change_type != "unchanged" for d in self.diffs)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "description": self.description,
            "summary": {
                "created": len(self.files_created),
                "modified": len(self.files_modified),
                "deleted": len(self.files_deleted),
            },
            "diffs": [d.to_dict() for d in self.diffs],
        }


class DiffTracker:
    """Tracks file changes during execution.
    
    Provides:
    - Before/after snapshots
    - Unified diff generation
    - Change set tracking
    - Rollback capability
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.snapshots_dir = self.workspace_root / ".snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self._before_snapshots: dict[str, FileSnapshot] = {}
        self._after_snapshots: dict[str, FileSnapshot] = {}
        self._change_sets: list[ChangeSet] = []
    
    async def capture_before(self, paths: list[Path]) -> dict[str, FileSnapshot]:
        """Capture before snapshots.
        
        Args:
            paths: List of paths to capture
            
        Returns:
            Dictionary of path -> snapshot
        """
        snapshots = {}
        for path in paths:
            path = Path(path)
            if not path.is_absolute():
                path = self.workspace_root / path
            snapshot = await FileSnapshot.capture(path)
            snapshots[str(path)] = snapshot
            self._before_snapshots[str(path)] = snapshot
        return snapshots
    
    async def capture_after(self, paths: list[Path]) -> dict[str, FileSnapshot]:
        """Capture after snapshots.
        
        Args:
            paths: List of paths to capture
            
        Returns:
            Dictionary of path -> snapshot
        """
        snapshots = {}
        for path in paths:
            path = Path(path)
            if not path.is_absolute():
                path = self.workspace_root / path
            snapshot = await FileSnapshot.capture(path)
            snapshots[str(path)] = snapshot
            self._after_snapshots[str(path)] = snapshot
        return snapshots
    
    async def compute_diff(self, path: Path) -> FileDiff:
        """Compute diff for a file.
        
        Args:
            path: Path to file
            
        Returns:
            FileDiff
        """
        path_str = str(path)
        old = self._before_snapshots.get(path_str)
        new = self._after_snapshots.get(path_str)
        
        # Determine change type
        if not old or not old.exists:
            if new and new.exists:
                change_type = "created"
            else:
                change_type = "unchanged"
        elif not new or not new.exists:
            change_type = "deleted"
        elif old.content_hash != new.content_hash:
            change_type = "modified"
        else:
            change_type = "unchanged"
        
        # Compute diff lines
        diff_lines = []
        if change_type in ("modified", "created") and new and new.exists:
            try:
                old_content = ""
                if old and old.exists:
                    old_content = await _read_file(path)
                new_content = await _read_file(path)
                
                diff_lines = list(difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{path.name}",
                    tofile=f"b/{path.name}",
                ))
            except Exception:
                pass
        
        return FileDiff(
            path=path_str,
            old_snapshot=old,
            new_snapshot=new,
            change_type=change_type,
            diff_lines=diff_lines,
        )
    
    async def compute_change_set(
        self,
        description: str = "",
        paths: Optional[list[Path]] = None,
    ) -> ChangeSet:
        """Compute a change set.
        
        Args:
            description: Description of the change
            paths: Optional specific paths (uses all tracked if not provided)
            
        Returns:
            ChangeSet
        """
        if paths is None:
            all_paths = set(self._before_snapshots.keys()) | set(self._after_snapshots.keys())
            paths = [Path(p) for p in all_paths]
        
        diffs = []
        for path in paths:
            diff = await self.compute_diff(path)
            diffs.append(diff)
        
        change_set = ChangeSet(
            id=hashlib.sha256(
                f"{datetime.now(timezone.utc).isoformat()}:{description}".encode()
            ).hexdigest()[:12],
            description=description,
            diffs=diffs,
        )
        
        self._change_sets.append(change_set)
        return change_set
    
    def get_change_sets(self) -> list[ChangeSet]:
        """Get all change sets.
        
        Returns:
            List of ChangeSet objects
        """
        return self._change_sets
    
    async def save_change_set(self, change_set: ChangeSet, path: Path) -> None:
        """Save a change set to file.
        
        Args:
            change_set: ChangeSet to save
            path: Path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, 'w') as f:
            await f.write(json.dumps(change_set.to_dict(), indent=2))
    
    def clear(self) -> None:
        """Clear all tracked snapshots and change sets."""
        self._before_snapshots.clear()
        self._after_snapshots.clear()
        self._change_sets.clear()
    
    async def scan_workspace(self, pattern: str = "**/*") -> list[Path]:
        """Scan workspace for files.
        
        Args:
            pattern: Glob pattern
            
        Returns:
            List of file paths
        """
        files = []
        for path in self.workspace_root.glob(pattern):
            if path.is_file() and not str(path).startswith(str(self.snapshots_dir)):
                files.append(path)
        return files
    
    async def track_all_changes(self, description: str = "") -> ChangeSet:
        """Track all changes in workspace.
        
        Captures before snapshots, waits for execution, then captures after.
        
        Args:
            description: Description of the change
            
        Returns:
            ChangeSet
        """
        # Capture all files
        files = await self.scan_workspace()
        await self.capture_before(files)
        
        # Note: In actual use, execution happens here
        
        # Capture after
        files_after = await self.scan_workspace()
        await self.capture_after(files_after)
        
        return await self.compute_change_set(description)
