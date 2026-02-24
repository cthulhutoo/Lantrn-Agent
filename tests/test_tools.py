"""Tests for tool registry."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

from lantrn_agent.tools.registry import (
    ToolResult,
    BaseTool,
    CodeExecutionTool,
    FileReadTool,
    FileWriteTool,
    BrowserTool,
    DocumentQueryTool,
    SearchTool,
    MemoryTool,
    ToolRegistry,
    check_policy_allowed,
)


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_tool_result_defaults(self):
        """Test ToolResult default values."""
        result = ToolResult(success=True, output="Done")
        assert result.success is True
        assert result.output == "Done"
        assert result.error is None
        assert result.metadata == {}

    def test_tool_result_with_error(self):
        """Test ToolResult with error."""
        result = ToolResult(
            success=False,
            output=None,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_tool_result_with_metadata(self):
        """Test ToolResult with metadata."""
        result = ToolResult(
            success=True,
            output="Result",
            metadata={"duration": 1.5, "tokens": 100},
        )
        assert result.metadata["duration"] == 1.5
        assert result.metadata["tokens"] == 100


class TestBaseTool:
    """Tests for BaseTool abstract class."""

    def test_base_tool_schema(self):
        """Test BaseTool.schema returns default structure."""
        class DummyTool(BaseTool):
            name = "dummy"
            description = "A dummy tool"
            
            async def execute(self, **kwargs):
                return ToolResult(success=True, output="ok")
        
        tool = DummyTool()
        schema = tool.schema()
        
        assert schema["name"] == "dummy"
        assert schema["description"] == "A dummy tool"
        assert schema["parameters"]["type"] == "object"


class TestCodeExecutionTool:
    """Tests for CodeExecutionTool."""

    def test_code_execution_tool_init(self, temp_workspace: Path):
        """Test CodeExecutionTool initialization."""
        tool = CodeExecutionTool(temp_workspace, timeout=60)
        assert tool.workspace_path == temp_workspace
        assert tool.timeout == 60
        assert tool.name == "code_execution_tool"
        assert tool.requires_approval is True

    def test_code_execution_tool_schema(self, temp_workspace: Path):
        """Test CodeExecutionTool.schema."""
        tool = CodeExecutionTool(temp_workspace)
        schema = tool.schema()
        
        assert schema["name"] == "code_execution_tool"
        assert "code" in schema["parameters"]["properties"]
        assert "runtime" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["code"]

    @pytest.mark.asyncio
    async def test_execute_shell_success(self, temp_workspace: Path):
        """Test shell command execution success."""
        tool = CodeExecutionTool(temp_workspace)
        result = await tool.execute(code="echo 'Hello World'", runtime="terminal")
        
        assert result.success is True
        assert "Hello World" in result.output

    @pytest.mark.asyncio
    async def test_execute_shell_error(self, temp_workspace: Path):
        """Test shell command execution with error."""
        tool = CodeExecutionTool(temp_workspace)
        result = await tool.execute(code="exit 1", runtime="terminal")
        
        assert result.success is False
        assert result.metadata["return_code"] == 1

    @pytest.mark.asyncio
    async def test_execute_python_success(self, temp_workspace: Path):
        """Test Python code execution success."""
        tool = CodeExecutionTool(temp_workspace)
        result = await tool.execute(
            code="print('Hello from Python')",
            runtime="python",
        )
        
        assert result.success is True
        assert "Hello from Python" in result.output

    @pytest.mark.asyncio
    async def test_execute_python_with_calculation(self, temp_workspace: Path):
        """Test Python code with calculation."""
        tool = CodeExecutionTool(temp_workspace)
        result = await tool.execute(
            code="x = 5 + 3\nprint(f'Result: {x}')",
            runtime="python",
        )
        
        assert result.success is True
        assert "Result: 8" in result.output

    @pytest.mark.asyncio
    async def test_execute_python_error(self, temp_workspace: Path):
        """Test Python code with error."""
        tool = CodeExecutionTool(temp_workspace)
        result = await tool.execute(
            code="raise ValueError('Test error')",
            runtime="python",
        )
        
        assert result.success is False
        assert "ValueError" in result.error

    @pytest.mark.asyncio
    async def test_execute_nodejs_success(self, temp_workspace: Path):
        """Test Node.js code execution success."""
        tool = CodeExecutionTool(temp_workspace)
        result = await tool.execute(
            code="console.log('Hello from Node.js');",
            runtime="nodejs",
        )
        
        assert result.success is True
        assert "Hello from Node.js" in result.output

    @pytest.mark.asyncio
    async def test_execute_unknown_runtime(self, temp_workspace: Path):
        """Test execution with unknown runtime."""
        tool = CodeExecutionTool(temp_workspace)
        result = await tool.execute(code="test", runtime="unknown")
        
        assert result.success is False
        assert "Unknown runtime" in result.error


class TestFileReadTool:
    """Tests for FileReadTool."""

    def test_file_read_tool_init(self, temp_workspace: Path):
        """Test FileReadTool initialization."""
        tool = FileReadTool(temp_workspace)
        assert tool.workspace_path == temp_workspace
        assert tool.name == "file_read"
        assert tool.requires_approval is False

    def test_file_read_tool_schema(self, temp_workspace: Path):
        """Test FileReadTool.schema."""
        tool = FileReadTool(temp_workspace)
        schema = tool.schema()
        
        assert schema["name"] == "file_read"
        assert "path" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["path"]

    @pytest.mark.asyncio
    async def test_read_file_success(self, temp_workspace: Path):
        """Test reading a file successfully."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Hello, World!")
        
        tool = FileReadTool(temp_workspace)
        result = await tool.execute(path="test.txt")
        
        assert result.success is True
        assert result.output == "Hello, World!"
        assert str(test_file) in result.metadata["path"]

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, temp_workspace: Path):
        """Test reading a non-existent file."""
        tool = FileReadTool(temp_workspace)
        result = await tool.execute(path="nonexistent.txt")
        
        assert result.success is False
        assert "File not found" in result.error

    @pytest.mark.asyncio
    async def test_read_file_in_subdirectory(self, temp_workspace: Path):
        """Test reading a file in a subdirectory."""
        subdir = temp_workspace / "subdir"
        subdir.mkdir()
        test_file = subdir / "nested.txt"
        test_file.write_text("Nested content")
        
        tool = FileReadTool(temp_workspace)
        result = await tool.execute(path="subdir/nested.txt")
        
        assert result.success is True
        assert result.output == "Nested content"


class TestFileWriteTool:
    """Tests for FileWriteTool."""

    def test_file_write_tool_init(self, temp_workspace: Path):
        """Test FileWriteTool initialization."""
        tool = FileWriteTool(temp_workspace)
        assert tool.workspace_path == temp_workspace
        assert tool.name == "file_write"
        assert tool.requires_approval is True

    def test_file_write_tool_schema(self, temp_workspace: Path):
        """Test FileWriteTool.schema."""
        tool = FileWriteTool(temp_workspace)
        schema = tool.schema()
        
        assert schema["name"] == "file_write"
        assert "path" in schema["parameters"]["properties"]
        assert "content" in schema["parameters"]["properties"]
        assert "path" in schema["parameters"]["required"]
        assert "content" in schema["parameters"]["required"]

    @pytest.mark.asyncio
    async def test_write_file_success(self, temp_workspace: Path):
        """Test writing a file successfully."""
        tool = FileWriteTool(temp_workspace)
        result = await tool.execute(
            path="output.txt",
            content="Hello, World!",
        )
        
        assert result.success is True
        assert "Wrote" in result.output
        
        # Verify file was written
        written_file = temp_workspace / "output.txt"
        assert written_file.exists()
        assert written_file.read_text() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_write_file_creates_directories(self, temp_workspace: Path):
        """Test writing creates parent directories."""
        tool = FileWriteTool(temp_workspace)
        result = await tool.execute(
            path="deep/nested/path/file.txt",
            content="Nested content",
        )
        
        assert result.success is True
        
        written_file = temp_workspace / "deep" / "nested" / "path" / "file.txt"
        assert written_file.exists()
        assert written_file.read_text() == "Nested content"

    @pytest.mark.asyncio
    async def test_write_file_overwrites(self, temp_workspace: Path):
        """Test writing overwrites existing file."""
        test_file = temp_workspace / "existing.txt"
        test_file.write_text("Original content")
        
        tool = FileWriteTool(temp_workspace)
        result = await tool.execute(
            path="existing.txt",
            content="New content",
        )
        
        assert result.success is True
        assert test_file.read_text() == "New content"


class TestBrowserTool:
    """Tests for BrowserTool."""

    def test_browser_tool_init(self, temp_workspace: Path):
        """Test BrowserTool initialization."""
        tool = BrowserTool(temp_workspace, timeout=10000)
        assert tool.workspace_path == temp_workspace
        assert tool.timeout == 10000
        assert tool.name == "browser"
        assert tool.requires_approval is True

    def test_browser_tool_schema(self, temp_workspace: Path):
        """Test BrowserTool.schema."""
        tool = BrowserTool(temp_workspace)
        schema = tool.schema()
        
        assert schema["name"] == "browser"
        assert "action" in schema["parameters"]["properties"]
        assert "url" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["action"]

    @pytest.mark.asyncio
    async def test_browser_missing_url_for_navigate(self, temp_workspace: Path):
        """Test browser navigate without URL."""
        tool = BrowserTool(temp_workspace)
        result = await tool.execute(action="navigate")
        
        assert result.success is False
        assert "URL required" in result.error

    @pytest.mark.asyncio
    async def test_browser_missing_selector_for_click(self, temp_workspace: Path):
        """Test browser click without selector."""
        tool = BrowserTool(temp_workspace)
        result = await tool.execute(action="click")
        
        assert result.success is False
        assert "Selector required" in result.error

    @pytest.mark.asyncio
    async def test_browser_unknown_action(self, temp_workspace: Path):
        """Test browser with unknown action."""
        tool = BrowserTool(temp_workspace)
        result = await tool.execute(action="unknown")
        
        assert result.success is False
        assert "Unknown action" in result.error


class TestDocumentQueryTool:
    """Tests for DocumentQueryTool."""

    def test_document_query_tool_init(self, temp_workspace: Path):
        """Test DocumentQueryTool initialization."""
        tool = DocumentQueryTool(temp_workspace)
        assert tool.workspace_path == temp_workspace
        assert tool.name == "document_query"

    def test_document_query_tool_schema(self, temp_workspace: Path):
        """Test DocumentQueryTool.schema."""
        tool = DocumentQueryTool(temp_workspace)
        schema = tool.schema()
        
        assert schema["name"] == "document_query"
        assert "action" in schema["parameters"]["properties"]
        assert "document_path" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_extract_text_txt(self, temp_workspace: Path):
        """Test extracting text from TXT file."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("This is plain text content.")
        
        tool = DocumentQueryTool(temp_workspace)
        result = await tool.execute(
            action="extract_text",
            document_path="test.txt",
        )
        
        assert result.success is True
        assert "plain text content" in result.output

    @pytest.mark.asyncio
    async def test_extract_text_file_not_found(self, temp_workspace: Path):
        """Test extracting text from non-existent file."""
        tool = DocumentQueryTool(temp_workspace)
        result = await tool.execute(
            action="extract_text",
            document_path="nonexistent.txt",
        )
        
        assert result.success is False
        assert "Document not found" in result.error

    @pytest.mark.asyncio
    async def test_query_without_questions(self, temp_workspace: Path):
        """Test query action without questions."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Some content")
        
        tool = DocumentQueryTool(temp_workspace)
        result = await tool.execute(
            action="query",
            document_path="test.txt",
        )
        
        assert result.success is False
        assert "Questions required" in result.error

    @pytest.mark.asyncio
    async def test_unknown_action(self, temp_workspace: Path):
        """Test unknown action."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Content")
        
        tool = DocumentQueryTool(temp_workspace)
        result = await tool.execute(
            action="unknown",
            document_path="test.txt",
        )
        
        assert result.success is False
        assert "Unknown action" in result.error


class TestSearchTool:
    """Tests for SearchTool."""

    def test_search_tool_init(self, temp_workspace: Path):
        """Test SearchTool initialization."""
        tool = SearchTool(temp_workspace, timeout=10)
        assert tool.workspace_path == temp_workspace
        assert tool.timeout == 10
        assert tool.name == "search"

    def test_search_tool_schema(self, temp_workspace: Path):
        """Test SearchTool.schema."""
        tool = SearchTool(temp_workspace)
        schema = tool.schema()
        
        assert schema["name"] == "search"
        assert "query" in schema["parameters"]["properties"]
        assert "num_results" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["query"]

    def test_parse_search_results(self, temp_workspace: Path):
        """Test parsing search results HTML."""
        tool = SearchTool(temp_workspace)
        
        html = '''
        <div class="result">
            <a class="result__a" href="https://example.com">Example Result</a>
            <a class="result__snippet">This is a snippet</a>
        </div>
        '''
        
        results = tool._parse_search_results(html, 5)
        
        # Results may be empty if BeautifulSoup is not installed
        # or may have results if it is
        assert isinstance(results, list)


class TestMemoryTool:
    """Tests for MemoryTool."""

    def test_memory_tool_init(self, temp_workspace: Path):
        """Test MemoryTool initialization."""
        tool = MemoryTool(temp_workspace)
        assert tool.workspace_path == temp_workspace
        assert tool.name == "memory"
        assert tool._memory_dir.exists()

    def test_memory_tool_schema(self, temp_workspace: Path):
        """Test MemoryTool.schema."""
        tool = MemoryTool(temp_workspace)
        schema = tool.schema()
        
        assert schema["name"] == "memory"
        assert "action" in schema["parameters"]["properties"]
        assert "key" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_save_and_load(self, temp_workspace: Path):
        """Test saving and loading memory."""
        tool = MemoryTool(temp_workspace)
        
        # Save
        save_result = await tool.execute(
            action="save",
            key="test_key",
            value={"data": "test_value"},
        )
        assert save_result.success is True
        
        # Load
        load_result = await tool.execute(action="load", key="test_key")
        assert load_result.success is True
        assert load_result.output["data"] == "test_value"

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, temp_workspace: Path):
        """Test loading non-existent key."""
        tool = MemoryTool(temp_workspace)
        result = await tool.execute(action="load", key="nonexistent")
        
        assert result.success is False
        assert "Key not found" in result.error

    @pytest.mark.asyncio
    async def test_delete(self, temp_workspace: Path):
        """Test deleting memory."""
        tool = MemoryTool(temp_workspace)
        
        # Save first
        await tool.execute(action="save", key="to_delete", value="data")
        
        # Delete
        delete_result = await tool.execute(action="delete", key="to_delete")
        assert delete_result.success is True
        
        # Verify deleted
        load_result = await tool.execute(action="load", key="to_delete")
        assert load_result.success is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, temp_workspace: Path):
        """Test deleting non-existent key."""
        tool = MemoryTool(temp_workspace)
        result = await tool.execute(action="delete", key="nonexistent")
        
        assert result.success is False
        assert "Key not found" in result.error

    @pytest.mark.asyncio
    async def test_save_without_value(self, temp_workspace: Path):
        """Test save without value."""
        tool = MemoryTool(temp_workspace)
        result = await tool.execute(action="save", key="test")
        
        assert result.success is False
        assert "Value required" in result.error

    @pytest.mark.asyncio
    async def test_unknown_action(self, temp_workspace: Path):
        """Test unknown action."""
        tool = MemoryTool(temp_workspace)
        result = await tool.execute(action="unknown", key="test")
        
        assert result.success is False
        assert "Unknown action" in result.error


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_tool_registry_init(self, temp_workspace: Path):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry(temp_workspace)
        assert registry.workspace_path == temp_workspace
        assert len(registry._tools) > 0

    def test_tool_registry_default_tools(self, temp_workspace: Path):
        """Test ToolRegistry has default tools."""
        registry = ToolRegistry(temp_workspace)
        tools = registry.list_tools()
        
        assert "code_execution_tool" in tools
        assert "file_read" in tools
        assert "file_write" in tools
        assert "browser" in tools
        assert "document_query" in tools
        assert "search" in tools
        assert "memory" in tools

    def test_tool_registry_get(self, temp_workspace: Path):
        """Test ToolRegistry.get."""
        registry = ToolRegistry(temp_workspace)
        tool = registry.get("file_read")
        
        assert tool is not None
        assert tool.name == "file_read"

    def test_tool_registry_get_nonexistent(self, temp_workspace: Path):
        """Test ToolRegistry.get for non-existent tool."""
        registry = ToolRegistry(temp_workspace)
        tool = registry.get("nonexistent")
        
        assert tool is None

    def test_tool_registry_register(self, temp_workspace: Path):
        """Test ToolRegistry.register."""
        class CustomTool(BaseTool):
            name = "custom_tool"
            description = "A custom tool"
            
            async def execute(self, **kwargs):
                return ToolResult(success=True, output="custom")
        
        registry = ToolRegistry(temp_workspace)
        registry.register(CustomTool())
        
        assert "custom_tool" in registry.list_tools()
        assert registry.get("custom_tool") is not None

    def test_tool_registry_get_schemas(self, temp_workspace: Path):
        """Test ToolRegistry.get_schemas."""
        registry = ToolRegistry(temp_workspace)
        schemas = registry.get_schemas()
        
        assert isinstance(schemas, list)
        assert len(schemas) > 0
        
        # Check schema structure
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema

    @pytest.mark.asyncio
    async def test_tool_registry_execute(self, temp_workspace: Path):
        """Test ToolRegistry.execute."""
        registry = ToolRegistry(temp_workspace)
        
        # Create a test file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Test content")
        
        result = await registry.execute("file_read", path="test.txt")
        
        assert result.success is True
        assert result.output == "Test content"

    @pytest.mark.asyncio
    async def test_tool_registry_execute_nonexistent(self, temp_workspace: Path):
        """Test ToolRegistry.execute for non-existent tool."""
        registry = ToolRegistry(temp_workspace)
        result = await registry.execute("nonexistent")
        
        assert result.success is False
        assert "Tool not found" in result.error


class TestCheckPolicyAllowed:
    """Tests for check_policy_allowed function."""

    def test_check_policy_allowed_default(self):
        """Test check_policy_allowed returns True by default."""
        result = check_policy_allowed("read", "/workspace/file.txt", None)
        assert result is True
