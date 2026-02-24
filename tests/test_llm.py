"""Tests for LLM adapters."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from lantrn_agent.models.llm import (
    Message,
    MessageRole,
    ChatResponse,
    LLMAdapter,
    OllamaAdapter,
    OpenAIAdapter,
    get_llm_adapter,
)


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.TOOL == "tool"

    def test_message_role_string_conversion(self):
        """Test MessageRole string conversion."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"


class TestMessage:
    """Tests for Message dataclass."""

    def test_message_creation(self):
        """Test Message creation with required fields."""
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_message_with_all_fields(self):
        """Test Message with all fields."""
        msg = Message(
            role=MessageRole.TOOL,
            content="Tool result",
            name="calculator",
            tool_calls=[{"id": "call_123", "function": {"name": "add"}}],
            tool_call_id="call_123",
        )
        assert msg.role == MessageRole.TOOL
        assert msg.name == "calculator"
        assert len(msg.tool_calls) == 1
        assert msg.tool_call_id == "call_123"


class TestChatResponse:
    """Tests for ChatResponse dataclass."""

    def test_chat_response_defaults(self):
        """Test ChatResponse default values."""
        response = ChatResponse(content="Hello", model="llama3.2:3b")
        assert response.content == "Hello"
        assert response.model == "llama3.2:3b"
        assert response.usage == {}
        assert response.tool_calls is None
        assert response.finish_reason == "stop"

    def test_chat_response_with_usage(self):
        """Test ChatResponse with usage data."""
        response = ChatResponse(
            content="Hello",
            model="llama3.2:3b",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 5


class TestOllamaAdapter:
    """Tests for OllamaAdapter class."""

    def test_ollama_adapter_initialization(self):
        """Test OllamaAdapter initialization."""
        adapter = OllamaAdapter(base_url="http://localhost:11434")
        assert adapter.base_url == "http://localhost:11434"
        assert adapter.client is not None

    def test_ollama_adapter_default_url(self):
        """Test OllamaAdapter default URL."""
        adapter = OllamaAdapter()
        assert adapter.base_url == "http://localhost:11434"

    def test_ollama_adapter_trailing_slash(self):
        """Test OllamaAdapter strips trailing slash."""
        adapter = OllamaAdapter(base_url="http://localhost:11434/")
        assert adapter.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_ollama_chat(self, mock_httpx_client, mock_ollama_chat_response):
        """Test OllamaAdapter chat method."""
        adapter = OllamaAdapter()
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ollama_chat_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]
        
        response = await adapter.chat(messages, model="llama3.2:3b")
        
        assert response.content == "This is a test response from the LLM."
        assert response.model == "llama3.2:3b"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 20
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_ollama_chat_with_temperature(self, mock_httpx_client, mock_ollama_chat_response):
        """Test OllamaAdapter chat with custom temperature."""
        adapter = OllamaAdapter()
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ollama_chat_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        await adapter.chat(messages, model="llama3.2:3b", temperature=0.5)
        
        # Verify temperature was passed
        call_args = mock_httpx_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["options"]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_ollama_chat_with_max_tokens(self, mock_httpx_client, mock_ollama_chat_response):
        """Test OllamaAdapter chat with max_tokens."""
        adapter = OllamaAdapter()
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ollama_chat_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        await adapter.chat(messages, model="llama3.2:3b", max_tokens=100)
        
        call_args = mock_httpx_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["options"]["num_predict"] == 100

    @pytest.mark.asyncio
    async def test_ollama_message_formatting(self, mock_httpx_client, mock_ollama_chat_response):
        """Test OllamaAdapter formats messages correctly."""
        adapter = OllamaAdapter()
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ollama_chat_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="Hello"),
        ]
        
        await adapter.chat(messages, model="llama3.2:3b")
        
        call_args = mock_httpx_client.post.call_args
        payload = call_args.kwargs["json"]
        
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are helpful."
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_ollama_embed_single(self, mock_httpx_client, mock_ollama_embedding_response):
        """Test OllamaAdapter embed with single text."""
        adapter = OllamaAdapter()
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ollama_embedding_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        embedding = await adapter.embed("Hello world", model="nomic-embed-text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 768

    @pytest.mark.asyncio
    async def test_ollama_embed_batch(self, mock_httpx_client, mock_ollama_embedding_response):
        """Test OllamaAdapter embed with batch of texts."""
        adapter = OllamaAdapter()
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ollama_embedding_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        embeddings = await adapter.embed(["Hello", "World"], model="nomic-embed-text")
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 2

    @pytest.mark.asyncio
    async def test_ollama_list_models(self, mock_httpx_client, mock_ollama_models_response):
        """Test OllamaAdapter list_models."""
        adapter = OllamaAdapter()
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = mock_ollama_models_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response
        
        models = await adapter.list_models()
        
        assert len(models) == 2
        assert "llama3.2:3b" in models
        assert "llama3.1:70b" in models


class TestOpenAIAdapter:
    """Tests for OpenAIAdapter class."""

    def test_openai_adapter_initialization(self):
        """Test OpenAIAdapter initialization."""
        adapter = OpenAIAdapter(api_key="test-key")
        assert adapter.api_key == "test-key"
        assert adapter.base_url == "https://api.openai.com/v1"

    def test_openai_adapter_custom_url(self):
        """Test OpenAIAdapter with custom URL."""
        adapter = OpenAIAdapter(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )
        assert adapter.base_url == "https://custom.api.com/v1"

    @pytest.mark.asyncio
    async def test_openai_chat(self, mock_httpx_client):
        """Test OpenAIAdapter chat method."""
        adapter = OpenAIAdapter(api_key="test-key")
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hello from GPT!"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        response = await adapter.chat(messages, model="gpt-4")
        
        assert response.content == "Hello from GPT!"
        assert response.model == "gpt-4"
        assert response.usage["prompt_tokens"] == 10

    @pytest.mark.asyncio
    async def test_openai_chat_with_max_tokens(self, mock_httpx_client):
        """Test OpenAIAdapter chat with max_tokens."""
        adapter = OpenAIAdapter(api_key="test-key")
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        messages = [Message(role=MessageRole.USER, content="Hello")]
        
        await adapter.chat(messages, model="gpt-4", max_tokens=50)
        
        call_args = mock_httpx_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["max_tokens"] == 50

    @pytest.mark.asyncio
    async def test_openai_message_formatting(self, mock_httpx_client):
        """Test OpenAIAdapter formats messages correctly."""
        adapter = OpenAIAdapter(api_key="test-key")
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        messages = [
            Message(role=MessageRole.SYSTEM, content="Be helpful"),
            Message(role=MessageRole.USER, content="Hello"),
        ]
        
        await adapter.chat(messages, model="gpt-4")
        
        call_args = mock_httpx_client.post.call_args
        payload = call_args.kwargs["json"]
        
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_openai_embed_single(self, mock_httpx_client):
        """Test OpenAIAdapter embed with single text."""
        adapter = OpenAIAdapter(api_key="test-key")
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1536}],
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        embedding = await adapter.embed("Hello world", model="text-embedding-3-small")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_openai_embed_batch(self, mock_httpx_client):
        """Test OpenAIAdapter embed with batch of texts."""
        adapter = OpenAIAdapter(api_key="test-key")
        adapter.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1] * 1536},
                {"embedding": [0.2] * 1536},
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response
        
        embeddings = await adapter.embed(["Hello", "World"], model="text-embedding-3-small")
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 2


class TestGetLLMAdapter:
    """Tests for get_llm_adapter factory function."""

    def test_get_ollama_adapter(self):
        """Test get_llm_adapter returns OllamaAdapter."""
        adapter = get_llm_adapter("ollama")
        assert isinstance(adapter, OllamaAdapter)

    def test_get_ollama_adapter_with_url(self):
        """Test get_llm_adapter with custom URL."""
        adapter = get_llm_adapter("ollama", base_url="http://custom:11434")
        assert adapter.base_url == "http://custom:11434"

    def test_get_openai_adapter(self):
        """Test get_llm_adapter returns OpenAIAdapter."""
        adapter = get_llm_adapter("openai", api_key="test-key")
        assert isinstance(adapter, OpenAIAdapter)

    def test_get_openai_adapter_requires_key(self):
        """Test get_llm_adapter raises error without API key."""
        with pytest.raises(ValueError, match="OpenAI API key required"):
            get_llm_adapter("openai")

    def test_get_openai_compatible_adapter(self):
        """Test get_llm_adapter for OpenAI-compatible provider."""
        adapter = get_llm_adapter(
            "openai_compatible",
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )
        assert isinstance(adapter, OpenAIAdapter)
        assert adapter.base_url == "https://custom.api.com/v1"

    def test_get_openai_compatible_requires_both(self):
        """Test get_llm_adapter raises error without key and URL."""
        with pytest.raises(ValueError, match="API key and base URL required"):
            get_llm_adapter("openai_compatible", api_key="test-key")
        
        with pytest.raises(ValueError, match="API key and base URL required"):
            get_llm_adapter("openai_compatible", base_url="https://custom.api.com/v1")

    def test_get_unknown_provider(self):
        """Test get_llm_adapter raises error for unknown provider."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_adapter("unknown")
