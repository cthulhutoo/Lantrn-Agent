"""LLM adapter for Ollama and cloud providers.

Provides a unified interface for model inference.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional

import httpx
from pydantic import BaseModel


class MessageRole(str, Enum):
    """Message role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in the conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ChatResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    tool_calls: Optional[list[dict]] = None
    finish_reason: str = "stop"


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""
    
    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Send a chat completion request."""
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response."""
        pass
    
    @abstractmethod
    async def embed(
        self,
        text: str | list[str],
        model: str,
    ) -> list[float] | list[list[float]]:
        """Generate embeddings for text."""
        pass


class OllamaAdapter(LLMAdapter):
    """Ollama LLM adapter for local models."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Send a chat completion request to Ollama."""
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": model,
            "messages": [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        return ChatResponse(
            content=data.get("message", {}).get("content", ""),
            model=model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            finish_reason="stop" if data.get("done") else "length",
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response from Ollama."""
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": model,
            "messages": [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ],
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        async with self.client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]
    
    async def embed(
        self,
        text: str | list[str],
        model: str = "nomic-embed-text",
    ) -> list[float] | list[list[float]]:
        """Generate embeddings using Ollama."""
        url = f"{self.base_url}/api/embeddings"
        
        if isinstance(text, str):
            payload = {"model": model, "prompt": text}
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["embedding"]
        else:
            # Batch embeddings
            embeddings = []
            for t in text:
                payload = {"model": model, "prompt": t}
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
            return embeddings
    
    async def list_models(self) -> list[str]:
        """List available models."""
        url = f"{self.base_url}/api/tags"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    
    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry."""
        url = f"{self.base_url}/api/pull"
        payload = {"name": model, "stream": False}
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return True


class OpenAIAdapter(LLMAdapter):
    """OpenAI API adapter."""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Send a chat completion request to OpenAI."""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ],
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        choice = data["choices"][0]
        return ChatResponse(
            content=choice["message"]["content"],
            model=model,
            usage=data.get("usage", {}),
            tool_calls=choice["message"].get("tool_calls"),
            finish_reason=choice.get("finish_reason", "stop"),
        )
    
    async def chat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response from OpenAI."""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": [
                {"role": msg.role.value, "content": msg.content}
                for msg in messages
            ],
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        async with self.client.stream("POST", url, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    import json
                    data = json.loads(line[6:])
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
    
    async def embed(
        self,
        text: str | list[str],
        model: str = "text-embedding-3-small",
    ) -> list[float] | list[list[float]]:
        """Generate embeddings using OpenAI."""
        url = f"{self.base_url}/embeddings"
        
        payload = {
            "model": model,
            "input": text,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(text, str):
            return data["data"][0]["embedding"]
        else:
            return [item["embedding"] for item in data["data"]]


def get_llm_adapter(
    provider: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMAdapter:
    """Factory function to get the appropriate LLM adapter."""
    if provider == "ollama":
        return OllamaAdapter(base_url or "http://localhost:11434")
    elif provider == "openai":
        if not api_key:
            raise ValueError("OpenAI API key required")
        return OpenAIAdapter(api_key, base_url)
    elif provider == "openai_compatible":
        if not api_key or not base_url:
            raise ValueError("API key and base URL required for OpenAI-compatible providers")
        return OpenAIAdapter(api_key, base_url)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
