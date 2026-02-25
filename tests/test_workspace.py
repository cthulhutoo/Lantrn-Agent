"""Tests for workspace management."""

import pytest
from pathlib import Path
import tempfile
import asyncio

from lantrn_agent.workspace.isolation import (
    IsolationContext,
    IsolationConfig,
    MultiServiceSupport,
)
from lantrn_agent.workspace.manifest import (
    RunManifest,
    RunStep,
    ManifestStore,
)
from lantrn_agent.workspace.diff_tracker import (
    DiffTracker,
    FileSnapshot,
    ChangeSet,
)
from lantrn_agent.workspace.manager import (
    WorkspaceManager,
    WorkspaceConfig,
    ContextPartition,
    PartitionManager,
)


class TestIsolationContext:
    """Tests for IsolationContext."""
    
    def test_create_context(self, temp_dir):
        """Test creating an isolation context."""
        context = IsolationContext(
            id="test-ctx",
            root=temp_dir / "workspace",
            config=IsolationConfig(enabled=True),
        )
        
        assert context.id == "test-ctx"
        assert context.config.enabled is True
    
    def test_setup_creates_directories(self, temp_dir):
        """Test that setup creates required directories."""
        context = IsolationContext(
            root=temp_dir / "workspace",
            config=IsolationConfig(enabled=True),
        )
        
        result = context.setup()
        
        assert result.exists()
        assert (result / "workspace").exists()
        assert (result / "output").exists()
        assert (result / "logs").exists()
        assert (result / "cache").exists()
    
    def test_isolated_context_manager(self, temp_dir):
        """Test the isolated context manager."""
        context = IsolationContext(
            root=temp_dir / "workspace",
            config=IsolationConfig(enabled=True, preserve_on_exit=True),
        )
        context.setup()
        
        with context.isolated() as workspace:
            assert workspace.exists()
            import os
            assert "LANTRN_WORKSPACE_ID" in os.environ
    
    def test_path_allowed_in_workspace(self, temp_dir):
        """Test that workspace paths are allowed."""
        context = IsolationContext(
            root=temp_dir / "workspace",
            config=IsolationConfig(enabled=True),
        )
        context.setup()
        
        assert context.is_path_allowed(context.root / "workspace" / "test.txt")
    
    def test_path_denied_outside_workspace(self, temp_dir):
        """Test that denied paths are blocked."""
        context = IsolationContext(
            root=temp_dir / "workspace",
            config=IsolationConfig(
                enabled=True,
                denied_paths=["/etc", "/root"],
            ),
        )
        context.setup()
        
        assert not context.is_path_allowed(Path("/etc/passwd"))


class TestMultiServiceSupport:
    """Tests for MultiServiceSupport."""
    
    def test_create_service(self, temp_dir):
        """Test creating a service context."""
        support = MultiServiceSupport(temp_dir)
        
        context = support.create_service("test-service")
        
        assert context is not None
        assert "test-service" in support.list_services()
    
    def test_get_service(self, temp_dir):
        """Test getting an existing service."""
        support = MultiServiceSupport(temp_dir)
        support.create_service("test-service")
        
        context = support.get_service("test-service")
        
        assert context is not None
    
    def test_cleanup_all(self, temp_dir):
        """Test cleaning up all services."""
        support = MultiServiceSupport(temp_dir)
        support.create_service("service1")
        support.create_service("service2")
        
        support.cleanup_all()
        
        assert len(support.list_services()) == 0


class TestRunManifest:
    """Tests for RunManifest."""
    
    def test_create_manifest(self):
        """Test creating a run manifest."""
        manifest = RunManifest(name="test-run")
        
        assert manifest.name == "test-run"
        assert manifest.status == "pending"
        assert manifest.id is not None
    
    def test_start_complete(self):
        """Test starting and completing a run."""
        manifest = RunManifest(name="test-run")
        
        manifest.start()
        assert manifest.status == "running"
        assert manifest.started_at is not None
        
        manifest.complete()
        assert manifest.status == "completed"
        assert manifest.completed_at is not None
    
    def test_add_step(self):
        """Test adding steps to a run."""
        manifest = RunManifest(name="test-run")
        
        step = manifest.add_step("analyze", "analyst")
        
        assert len(manifest.steps) == 1
        assert step.name == "analyze"
        assert step.agent == "analyst"
    
    def test_step_lifecycle(self):
        """Test step lifecycle methods."""
        step = RunStep(name="test", agent="analyst")
        
        step.start()
        assert step.status == "running"
        
        step.complete({"result": "done"})
        assert step.status == "completed"
        assert step.output_data == {"result": "done"}
    
    def test_step_failure(self):
        """Test step failure."""
        step = RunStep(name="test", agent="analyst")
        
        step.start()
        step.fail("Something went wrong")
        
        assert step.status == "failed"
        assert step.error == "Something went wrong"
    
    def test_serialize_deserialize(self):
        """Test JSON serialization."""
        manifest = RunManifest(name="test-run")
        manifest.add_step("step1", "analyst")
        manifest.start()
        
        json_str = manifest.to_json()
        loaded = RunManifest.from_json(json_str)
        
        assert loaded.name == manifest.name
        assert len(loaded.steps) == 1
    
    def test_save_load(self, temp_dir):
        """Test saving and loading manifest."""
        manifest = RunManifest(name="test-run")
        manifest.add_step("step1", "analyst")
        
        path = temp_dir / "manifest.json"
        manifest.save(path)
        
        loaded = RunManifest.load(path)
        assert loaded.name == "test-run"


class TestManifestStore:
    """Tests for ManifestStore."""
    
    def test_save_load(self, temp_dir):
        """Test saving and loading manifests."""
        store = ManifestStore(temp_dir)
        manifest = RunManifest(name="test-run")
        
        path = store.save(manifest)
        assert path.exists()
        
        loaded = store.load(manifest.id)
        assert loaded is not None
        assert loaded.name == "test-run"
    
    def test_list_runs(self, temp_dir):
        """Test listing runs."""
        store = ManifestStore(temp_dir)
        
        # Create multiple runs
        for i in range(3):
            manifest = RunManifest(name=f"run-{i}")
            manifest.start()
            if i < 2:
                manifest.complete()
            else:
                manifest.fail("error")
            store.save(manifest)
        
        all_runs = store.list_runs()
        assert len(all_runs) == 3
        
        completed = store.list_runs(status="completed")
        assert len(completed) == 2


class TestDiffTracker:
    """Tests for DiffTracker."""
    
    @pytest.mark.asyncio
    async def test_capture_snapshot(self, temp_dir):
        """Test capturing file snapshots."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello world")
        
        snapshot = await FileSnapshot.capture(test_file)
        
        assert snapshot.exists
        assert snapshot.size == 11
        assert len(snapshot.content_hash) == 64
    
    @pytest.mark.asyncio
    async def test_snapshot_nonexistent(self, temp_dir):
        """Test snapshot of nonexistent file."""
        snapshot = await FileSnapshot.capture(temp_dir / "nonexistent.txt")
        
        assert not snapshot.exists
    
    @pytest.mark.asyncio
    async def test_compute_diff_created(self, temp_dir):
        """Test diff for created file."""
        tracker = DiffTracker(temp_dir)
        
        # Capture before (file doesn't exist)
        await tracker.capture_before([temp_dir / "new.txt"])
        
        # Create file
        (temp_dir / "new.txt").write_text("new content")
        
        # Capture after
        await tracker.capture_after([temp_dir / "new.txt"])
        
        diff = await tracker.compute_diff(temp_dir / "new.txt")
        assert diff.change_type == "created"
    
    @pytest.mark.asyncio
    async def test_compute_diff_modified(self, temp_dir):
        """Test diff for modified file."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("original")
        
        tracker = DiffTracker(temp_dir)
        await tracker.capture_before([test_file])
        
        test_file.write_text("modified")
        await tracker.capture_after([test_file])
        
        diff = await tracker.compute_diff(test_file)
        assert diff.change_type == "modified"
    
    @pytest.mark.asyncio
    async def test_compute_change_set(self, temp_dir):
        """Test computing a change set."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("original")
        
        tracker = DiffTracker(temp_dir)
        await tracker.capture_before([test_file])
        
        test_file.write_text("modified")
        await tracker.capture_after([test_file])
        
        change_set = await tracker.compute_change_set("Test changes")
        
        assert change_set.has_changes
        assert len(change_set.files_modified) == 1


class TestWorkspaceManager:
    """Tests for WorkspaceManager."""
    
    def test_create_workspace(self, temp_dir):
        """Test creating a workspace."""
        config = WorkspaceConfig(root=temp_dir)
        manager = WorkspaceManager(config)
        
        ws_id, context = manager.create_workspace("test-ws")
        
        assert ws_id == "test-ws"
        assert context.root.exists()
    
    def test_get_workspace(self, temp_dir):
        """Test getting a workspace."""
        config = WorkspaceConfig(root=temp_dir)
        manager = WorkspaceManager(config)
        manager.create_workspace("test-ws")
        
        context = manager.get_workspace("test-ws")
        assert context is not None
    
    def test_list_workspaces(self, temp_dir):
        """Test listing workspaces."""
        config = WorkspaceConfig(root=temp_dir)
        manager = WorkspaceManager(config)
        manager.create_workspace("ws1")
        manager.create_workspace("ws2")
        
        workspaces = manager.list_workspaces()
        assert len(workspaces) == 2
    
    @pytest.mark.asyncio
    async def test_start_complete_run(self, temp_dir):
        """Test starting and completing a run."""
        config = WorkspaceConfig(root=temp_dir)
        manager = WorkspaceManager(config)
        ws_id, _ = manager.create_workspace("test-ws")
        
        manifest = await manager.start_run(ws_id, "test-run")
        assert manifest is not None
        assert manifest.status == "running"
        
        change_set = await manager.complete_run(ws_id, manifest, success=True)
        assert manifest.status == "completed"
    
    def test_cleanup_workspace(self, temp_dir):
        """Test cleaning up a workspace."""
        config = WorkspaceConfig(root=temp_dir, auto_cleanup=True)
        manager = WorkspaceManager(config)
        manager.create_workspace("test-ws")
        
        result = manager.cleanup_workspace("test-ws")
        assert result is True
        assert manager.get_workspace("test-ws") is None


class TestPartitionManager:
    """Tests for PartitionManager."""
    
    def test_create_partition(self, temp_dir):
        """Test creating a partition."""
        config = WorkspaceConfig(root=temp_dir)
        manager = WorkspaceManager(config)
        ws_id, _ = manager.create_workspace("test-ws")
        
        partition_mgr = PartitionManager(manager)
        partition = partition_mgr.create_partition(ws_id, "partition1")
        
        assert partition is not None
        assert partition.partition_id == "partition1"
    
    def test_list_partitions(self, temp_dir):
        """Test listing partitions."""
        config = WorkspaceConfig(root=temp_dir)
        manager = WorkspaceManager(config)
        ws_id, _ = manager.create_workspace("test-ws")
        
        partition_mgr = PartitionManager(manager)
        partition_mgr.create_partition(ws_id, "p1")
        partition_mgr.create_partition(ws_id, "p2")
        
        partitions = partition_mgr.list_partitions(ws_id)
        assert len(partitions) == 2
