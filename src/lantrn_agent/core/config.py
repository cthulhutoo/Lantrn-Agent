"""Configuration system for Lantrn Agent Builder.

YAML-based configuration with environment variable support.
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ModelProfile(BaseModel):
    """Configuration for a model profile."""
    provider: str = "ollama"
    model: str = "llama3.2:3b"
    ctx_length: int = 128000
    temperature: float = 0.7
    api_base: Optional[str] = None
    

class BudgetConfig(BaseModel):
    """Resource budget limits."""
    max_tokens_per_task: int = 100000
    max_file_size_mb: int = 50
    max_execution_time_minutes: int = 30
    max_files_per_task: int = 100
    max_network_requests: int = 50


class FileAccessConfig(BaseModel):
    """File access control configuration."""
    default: str = "deny"
    allow: list[str] = Field(default_factory=lambda: ["workspace/**", "/tmp/**"])
    deny: list[str] = Field(default_factory=lambda: ["~/.ssh/**", "**/.credentials"])


class NetworkAccessConfig(BaseModel):
    """Network access control configuration."""
    default: str = "deny"
    allow: list[str] = Field(default_factory=lambda: ["localhost:11434", "127.0.0.1:11434"])
    deny: list[str] = Field(default_factory=lambda: ["*"])


class ToolAccessConfig(BaseModel):
    """Tool access control configuration."""
    default: str = "allow"
    deny: list[str] = Field(default_factory=list)
    require_approval: list[str] = Field(default_factory=lambda: ["browser_agent"])


class ExecutionConfig(BaseModel):
    """Execution environment configuration."""
    sandbox_enabled: bool = True
    allow_network: bool = True
    allow_file_write: bool = True
    allow_subprocess: bool = True
    max_subprocess_count: int = 5


class AuditConfig(BaseModel):
    """Audit logging configuration."""
    log_all_actions: bool = True
    log_file_changes: bool = True
    log_network_requests: bool = True
    log_tool_calls: bool = True
    retention_days: int = 90


class PolicyConfig(BaseModel):
    """Complete policy configuration."""
    version: str = "1.0"
    name: str = "default-policy"
    file_access: FileAccessConfig = Field(default_factory=FileAccessConfig)
    network_access: NetworkAccessConfig = Field(default_factory=NetworkAccessConfig)
    tool_access: ToolAccessConfig = Field(default_factory=ToolAccessConfig)
    budgets: BudgetConfig = Field(default_factory=BudgetConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Lantrn Agent Builder"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Paths
    workspace_path: Path = Path("./workspace")
    config_path: Path = Path("./config")
    logs_path: Path = Path("./logs")
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "sqlite:///./lantrn.db"
    vector_db_path: Path = Path("./chroma_db")
    
    # LLM
    default_model_profile: str = "fast"
    ollama_base_url: str = "http://localhost:11434"
    
    # API Keys (optional, for cloud providers)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    class Config:
        env_prefix = "LANTRN_"
        env_file = ".env"
        extra = "ignore"


class ConfigManager:
    """Manages configuration loading and access."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("./config")
        self.settings = Settings()
        self._model_profiles: dict[str, ModelProfile] = {}
        self._policies: dict[str, PolicyConfig] = {}
        self._load_configs()
    
    def _load_configs(self) -> None:
        """Load all configuration files."""
        self._load_model_profiles()
        self._load_policies()
    
    def _load_model_profiles(self) -> None:
        """Load model profiles from YAML files."""
        profiles_dir = self.config_dir / "profiles"
        if profiles_dir.exists():
            for profile_file in profiles_dir.glob("*.yaml"):
                with open(profile_file) as f:
                    data = yaml.safe_load(f)
                    if data:
                        profile_name = profile_file.stem
                        self._model_profiles[profile_name] = ModelProfile(**data)
        
        # Default profiles if none loaded
        if not self._model_profiles:
            self._model_profiles = {
                "fast": ModelProfile(
                    provider="ollama",
                    model="llama3.2:3b",
                    ctx_length=128000,
                    temperature=0.7,
                ),
                "hq": ModelProfile(
                    provider="ollama",
                    model="llama3.1:70b",
                    ctx_length=128000,
                    temperature=0.3,
                ),
                "offline": ModelProfile(
                    provider="ollama",
                    model="llama3.1:70b",
                    ctx_length=128000,
                    temperature=0.5,
                ),
            }
    
    def _load_policies(self) -> None:
        """Load policies from YAML files."""
        policies_dir = self.config_dir / "policies"
        if policies_dir.exists():
            for policy_file in policies_dir.glob("*.yaml"):
                with open(policy_file) as f:
                    data = yaml.safe_load(f)
                    if data:
                        policy_name = data.get("name", policy_file.stem)
                        self._policies[policy_name] = PolicyConfig(**data)
        
        # Default policy if none loaded
        if not self._policies:
            self._policies["default-policy"] = PolicyConfig()
    
    def get_model_profile(self, name: str) -> ModelProfile:
        """Get a model profile by name."""
        if name not in self._model_profiles:
            raise ValueError(f"Model profile '{name}' not found")
        return self._model_profiles[name]
    
    def get_policy(self, name: str = "default-policy") -> PolicyConfig:
        """Get a policy by name."""
        if name not in self._policies:
            raise ValueError(f"Policy '{name}' not found")
        return self._policies[name]
    
    def list_model_profiles(self) -> list[str]:
        """List available model profiles."""
        return list(self._model_profiles.keys())
    
    def list_policies(self) -> list[str]:
        """List available policies."""
        return list(self._policies.keys())


# Global config instance
config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global configuration manager."""
    global config
    if config is None:
        config = ConfigManager()
    return config


def init_config(config_dir: Optional[Path] = None) -> ConfigManager:
    """Initialize the global configuration."""
    global config
    config = ConfigManager(config_dir)
    return config
