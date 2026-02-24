"""Tests for the configuration system."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from lantrn_agent.core.config import (
    ConfigManager,
    ModelProfile,
    PolicyConfig,
    Settings,
    BudgetConfig,
    FileAccessConfig,
    NetworkAccessConfig,
    ToolAccessConfig,
    ExecutionConfig,
    AuditConfig,
    get_config,
    init_config,
)


class TestModelProfile:
    """Tests for ModelProfile model."""

    def test_model_profile_defaults(self):
        """Test ModelProfile default values."""
        profile = ModelProfile()
        assert profile.provider == "ollama"
        assert profile.model == "llama3.2:3b"
        assert profile.ctx_length == 128000
        assert profile.temperature == 0.7
        assert profile.api_base is None

    def test_model_profile_custom_values(self):
        """Test ModelProfile with custom values."""
        profile = ModelProfile(
            provider="openai",
            model="gpt-4",
            ctx_length=8000,
            temperature=0.3,
            api_base="https://api.openai.com/v1",
        )
        assert profile.provider == "openai"
        assert profile.model == "gpt-4"
        assert profile.ctx_length == 8000
        assert profile.temperature == 0.3
        assert profile.api_base == "https://api.openai.com/v1"


class TestBudgetConfig:
    """Tests for BudgetConfig model."""

    def test_budget_config_defaults(self):
        """Test BudgetConfig default values."""
        config = BudgetConfig()
        assert config.max_tokens_per_task == 100000
        assert config.max_file_size_mb == 50
        assert config.max_execution_time_minutes == 30
        assert config.max_files_per_task == 100
        assert config.max_network_requests == 50


class TestFileAccessConfig:
    """Tests for FileAccessConfig model."""

    def test_file_access_config_defaults(self):
        """Test FileAccessConfig default values."""
        config = FileAccessConfig()
        assert config.default == "deny"
        assert "workspace/**" in config.allow
        assert "/tmp/**" in config.allow
        assert "~/.ssh/**" in config.deny
        assert "**/.credentials" in config.deny


class TestNetworkAccessConfig:
    """Tests for NetworkAccessConfig model."""

    def test_network_access_config_defaults(self):
        """Test NetworkAccessConfig default values."""
        config = NetworkAccessConfig()
        assert config.default == "deny"
        assert "localhost:11434" in config.allow
        assert "*" in config.deny


class TestToolAccessConfig:
    """Tests for ToolAccessConfig model."""

    def test_tool_access_config_defaults(self):
        """Test ToolAccessConfig default values."""
        config = ToolAccessConfig()
        assert config.default == "allow"
        assert "browser_agent" in config.require_approval


class TestExecutionConfig:
    """Tests for ExecutionConfig model."""

    def test_execution_config_defaults(self):
        """Test ExecutionConfig default values."""
        config = ExecutionConfig()
        assert config.sandbox_enabled is True
        assert config.allow_network is True
        assert config.allow_file_write is True
        assert config.allow_subprocess is True
        assert config.max_subprocess_count == 5


class TestAuditConfig:
    """Tests for AuditConfig model."""

    def test_audit_config_defaults(self):
        """Test AuditConfig default values."""
        config = AuditConfig()
        assert config.log_all_actions is True
        assert config.log_file_changes is True
        assert config.log_network_requests is True
        assert config.log_tool_calls is True
        assert config.retention_days == 90


class TestPolicyConfig:
    """Tests for PolicyConfig model."""

    def test_policy_config_defaults(self):
        """Test PolicyConfig default values."""
        config = PolicyConfig()
        assert config.version == "1.0"
        assert config.name == "default-policy"
        assert isinstance(config.file_access, FileAccessConfig)
        assert isinstance(config.network_access, NetworkAccessConfig)
        assert isinstance(config.tool_access, ToolAccessConfig)
        assert isinstance(config.budgets, BudgetConfig)
        assert isinstance(config.execution, ExecutionConfig)
        assert isinstance(config.audit, AuditConfig)


class TestSettings:
    """Tests for Settings model."""

    def test_settings_defaults(self):
        """Test Settings default values."""
        settings = Settings()
        assert settings.app_name == "Lantrn Agent Builder"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.default_model_profile == "fast"
        assert settings.ollama_base_url == "http://localhost:11434"

    def test_settings_env_prefix(self):
        """Test Settings environment variable prefix."""
        with patch.dict(os.environ, {"LANTRN_DEBUG": "true", "LANTRN_PORT": "9000"}):
            settings = Settings()
            assert settings.debug is True
            assert settings.port == 9000

    def test_settings_path_conversion(self):
        """Test Settings path conversion."""
        settings = Settings(workspace_path="./custom_workspace")
        assert isinstance(settings.workspace_path, Path)


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_config_manager_initialization(self, temp_config_dir: Path):
        """Test ConfigManager initialization."""
        manager = ConfigManager(temp_config_dir)
        assert manager.config_dir == temp_config_dir
        assert isinstance(manager.settings, Settings)

    def test_config_manager_default_profiles(self, temp_dir: Path):
        """Test ConfigManager creates default profiles when none exist."""
        empty_config = temp_dir / "config"
        empty_config.mkdir()
        manager = ConfigManager(empty_config)
        
        profiles = manager.list_model_profiles()
        assert "fast" in profiles
        assert "hq" in profiles
        assert "offline" in profiles

    def test_config_manager_load_profiles(self, temp_config_dir: Path):
        """Test ConfigManager loads profiles from YAML files."""
        manager = ConfigManager(temp_config_dir)
        
        profile = manager.get_model_profile("fast")
        assert profile.provider == "ollama"
        assert profile.model == "llama3.2:3b"
        assert profile.temperature == 0.7

    def test_config_manager_get_nonexistent_profile(self, temp_config_dir: Path):
        """Test ConfigManager raises error for nonexistent profile."""
        manager = ConfigManager(temp_config_dir)
        
        with pytest.raises(ValueError, match="Model profile 'nonexistent' not found"):
            manager.get_model_profile("nonexistent")

    def test_config_manager_default_policy(self, temp_dir: Path):
        """Test ConfigManager creates default policy when none exists."""
        empty_config = temp_dir / "config"
        empty_config.mkdir()
        manager = ConfigManager(empty_config)
        
        policies = manager.list_policies()
        assert "default-policy" in policies

    def test_config_manager_load_policies(self, temp_config_dir: Path):
        """Test ConfigManager loads policies from YAML files."""
        manager = ConfigManager(temp_config_dir)
        
        policy = manager.get_policy("test-policy")
        assert policy.name == "test-policy"
        assert policy.version == "1.0"

    def test_config_manager_get_nonexistent_policy(self, temp_config_dir: Path):
        """Test ConfigManager raises error for nonexistent policy."""
        manager = ConfigManager(temp_config_dir)
        
        with pytest.raises(ValueError, match="Policy 'nonexistent' not found"):
            manager.get_policy("nonexistent")

    def test_config_manager_list_profiles(self, temp_config_dir: Path):
        """Test ConfigManager list_model_profiles."""
        manager = ConfigManager(temp_config_dir)
        profiles = manager.list_model_profiles()
        assert isinstance(profiles, list)
        assert "fast" in profiles

    def test_config_manager_list_policies(self, temp_config_dir: Path):
        """Test ConfigManager list_policies."""
        manager = ConfigManager(temp_config_dir)
        policies = manager.list_policies()
        assert isinstance(policies, list)
        assert "test-policy" in policies


class TestGlobalConfig:
    """Tests for global config functions."""

    def test_get_config_creates_instance(self):
        """Test get_config creates instance when none exists."""
        config = get_config()
        assert isinstance(config, ConfigManager)

    def test_get_config_returns_same_instance(self):
        """Test get_config returns same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_init_config_creates_new_instance(self, temp_config_dir: Path):
        """Test init_config creates new instance."""
        config = init_config(temp_config_dir)
        assert isinstance(config, ConfigManager)
        assert config.config_dir == temp_config_dir

    def test_init_config_updates_global(self, temp_config_dir: Path):
        """Test init_config updates global instance."""
        config = init_config(temp_config_dir)
        global_config = get_config()
        assert config is global_config


class TestConfigYAMLLoading:
    """Tests for YAML configuration loading."""

    def test_load_custom_profile(self, temp_config_dir: Path):
        """Test loading a custom model profile."""
        profiles_dir = temp_config_dir / "profiles"
        custom_profile = {
            "provider": "openai",
            "model": "gpt-4-turbo",
            "ctx_length": 128000,
            "temperature": 0.2,
            "api_base": "https://api.openai.com/v1",
        }
        with open(profiles_dir / "custom.yaml", "w") as f:
            yaml.dump(custom_profile, f)
        
        manager = ConfigManager(temp_config_dir)
        profile = manager.get_model_profile("custom")
        
        assert profile.provider == "openai"
        assert profile.model == "gpt-4-turbo"
        assert profile.temperature == 0.2

    def test_load_custom_policy(self, temp_config_dir: Path):
        """Test loading a custom policy."""
        policies_dir = temp_config_dir / "policies"
        custom_policy = {
            "version": "2.0",
            "name": "custom-policy",
            "file_access": {
                "default": "allow",
                "allow": ["**"],
                "deny": [],
            },
        }
        with open(policies_dir / "custom.yaml", "w") as f:
            yaml.dump(custom_policy, f)
        
        manager = ConfigManager(temp_config_dir)
        policy = manager.get_policy("custom-policy")
        
        assert policy.version == "2.0"
        assert policy.name == "custom-policy"
        assert policy.file_access.default == "allow"

    def test_empty_yaml_file_handling(self, temp_config_dir: Path):
        """Test handling of empty YAML files."""
        profiles_dir = temp_config_dir / "profiles"
        with open(profiles_dir / "empty.yaml", "w") as f:
            f.write("")
        
        manager = ConfigManager(temp_config_dir)
        # Should not crash, should use defaults
        assert "fast" in manager.list_model_profiles()
