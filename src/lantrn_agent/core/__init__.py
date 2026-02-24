"""Core module for Lantrn Agent Builder."""

from .config import ConfigManager, Settings, PolicyConfig, ModelProfile, init_config, get_config
from .memory import (
    MemoryManager,
    MemoryEntry,
    ConversationEntry,
    TraceEntry,
    get_memory_manager,
    init_memory_manager,
)

# Lazy import for pipeline to avoid circular imports
def __getattr__(name):
    if name in ("Pipeline", "Blueprint", "RunManifest"):
        from .pipeline import Pipeline, Blueprint, RunManifest
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ConfigManager",
    "Settings",
    "PolicyConfig",
    "ModelProfile",
    "init_config",
    "get_config",
    "Pipeline",
    "Blueprint",
    "RunManifest",
    "MemoryManager",
    "MemoryEntry",
    "ConversationEntry",
    "TraceEntry",
    "get_memory_manager",
    "init_memory_manager",
]
