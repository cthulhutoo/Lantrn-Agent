"""Tool registry for agent execution.

Provides a registry of tools that agents can use.
"""

import asyncio
import subprocess
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional
import shutil
import aiofiles
import hashlib
from lantrn_agent.tools.base import BaseTool, ToolResult
from lantrn_agent.tools.test_runner import TestRunnerTool, CodeValidatorTool

def check_policy_allowed(action: str, resource: str, policy) -> bool:
    """Check if an action is allowed by policy."""
    # Simplified policy check - in production this would be more robust
    return True

class CodeExecutionTool(BaseTool):
    """Execute code in various runtimes."""
    
    name = "code_execution_tool"
    description = "Execute code in Python, Node.js, or shell"
    requires_approval = True
    
    def __init__(self, workspace_path: Path, timeout: int = 300):
        self.workspace_path = workspace_path
        self.timeout = timeout
    
    async def execute(
        self,
        code: str,
        runtime: str = "python",
        session: int = 0,
    ) -> ToolResult:
        """Execute code in the specified runtime."""
        try:
            if runtime == "terminal":
                return await self._execute_shell(code)
            elif runtime == "python":
                return await self._execute_python(code)
            elif runtime == "nodejs":
                return await self._execute_nodejs(code)
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown runtime: {runtime}",
                )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output=None,
                error=f"Execution timed out after {self.timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
    
    async def _execute_shell(self, command: str) -> ToolResult:
        """Execute a shell command."""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workspace_path,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            return ToolResult(
                success=process.returncode == 0,
                output=output,
                error=error if error else None,
                metadata={"return_code": process.returncode},
            )
        except asyncio.TimeoutError:
            process.kill()
            raise
    
    async def _execute_python(self, code: str) -> ToolResult:
        """Execute Python code."""
        # Write code to temp file
        temp_file = self.workspace_path / f"_temp_{id(self)}.py"
        async with aiofiles.open(temp_file, "w") as f:
            await f.write(code)
        
        try:
            process = await asyncio.create_subprocess_exec(
                "python3",
                str(temp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_path,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            return ToolResult(
                success=process.returncode == 0,
                output=output,
                error=error if error else None,
                metadata={"return_code": process.returncode},
            )
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    async def _execute_nodejs(self, code: str) -> ToolResult:
        """Execute Node.js code."""
        temp_file = self.workspace_path / f"_temp_{id(self)}.js"
        async with aiofiles.open(temp_file, "w") as f:
            await f.write(code)
        
        try:
            process = await asyncio.create_subprocess_exec(
                "node",
                str(temp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_path,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            return ToolResult(
                success=process.returncode == 0,
                output=output,
                error=error if error else None,
                metadata={"return_code": process.returncode},
            )
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The code to execute",
                    },
                    "runtime": {
                        "type": "string",
                        "enum": ["python", "nodejs", "terminal"],
                        "default": "python",
                    },
                },
                "required": ["code"],
            },
        }

class FileReadTool(BaseTool):
    """Read file contents."""
    
    name = "file_read"
    description = "Read the contents of a file"
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
    
    async def execute(self, path: str) -> ToolResult:
        """Read file contents."""
        try:
            file_path = self.workspace_path / path
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {path}",
                )
            
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
            
            return ToolResult(
                success=True,
                output=content,
                metadata={"path": str(file_path)},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    },
                },
                "required": ["path"],
            },
        }

class FileWriteTool(BaseTool):
    """Write content to a file."""
    
    name = "file_write"
    description = "Write content to a file"
    requires_approval = True
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
    
    async def execute(self, path: str, content: str) -> ToolResult:
        """Write content to file."""
        try:
            file_path = self.workspace_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, "w") as f:
                await f.write(content)
            
            return ToolResult(
                success=True,
                output=f"Wrote {len(content)} characters to {path}",
                metadata={"path": str(file_path), "size": len(content)},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        }

class BrowserTool(BaseTool):
    """Web browsing and automation using Playwright."""
    
    name = "browser"
    description = "Web browsing and automation - navigate, screenshot, click, fill forms, extract content"
    requires_approval = True
    
    def __init__(self, workspace_path: Path, timeout: int = 30000):
        self.workspace_path = workspace_path
        self.timeout = timeout
        self._browser = None
        self._page = None
        self._playwright = None
    
    async def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self._page is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
                self._page = await self._browser.new_page()
            except ImportError:
                raise RuntimeError("playwright not installed. Run: pip install playwright && playwright install chromium")
        return self._page
    
    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        screenshot_path: Optional[str] = None,
    ) -> ToolResult:
        """Execute browser action.
        
        Args:
            action: One of 'navigate', 'screenshot', 'click', 'fill', 'extract'
            url: URL to navigate to (for navigate action)
            selector: CSS selector (for click, fill, extract actions)
            text: Text to fill (for fill action)
            screenshot_path: Path to save screenshot (for screenshot action)
        """
        try:
            page = await self._ensure_browser()
            
            if action == "navigate":
                if not url:
                    return ToolResult(success=False, output=None, error="URL required for navigate action")
                await page.goto(url, timeout=self.timeout)
                return ToolResult(
                    success=True,
                    output=f"Navigated to {url}",
                    metadata={"url": url, "title": await page.title()}
                )
            
            elif action == "screenshot":
                save_path = screenshot_path or "screenshot.png"
                full_path = self.workspace_path / save_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(full_path))
                return ToolResult(
                    success=True,
                    output=f"Screenshot saved to {save_path}",
                    metadata={"path": str(full_path)}
                )
            
            elif action == "click":
                if not selector:
                    return ToolResult(success=False, output=None, error="Selector required for click action")
                await page.click(selector, timeout=self.timeout)
                return ToolResult(
                    success=True,
                    output=f"Clicked element: {selector}",
                    metadata={"selector": selector}
                )
            
            elif action == "fill":
                if not selector or text is None:
                    return ToolResult(success=False, output=None, error="Selector and text required for fill action")
                await page.fill(selector, text, timeout=self.timeout)
                return ToolResult(
                    success=True,
                    output=f"Filled '{text}' into {selector}",
                    metadata={"selector": selector, "text": text}
                )
            
            elif action == "extract":
                if not selector:
                    return ToolResult(success=False, output=None, error="Selector required for extract action")
                elements = await page.query_selector_all(selector)
                results = []
                for el in elements:
                    text_content = await el.text_content()
                    results.append(text_content)
                return ToolResult(
                    success=True,
                    output=results,
                    metadata={"selector": selector, "count": len(results)}
                )
            
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown action: {action}. Valid actions: navigate, screenshot, click, fill, extract"
                )
                
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    async def close(self):
        """Close browser resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["navigate", "screenshot", "click", "fill", "extract"],
                        "description": "Browser action to perform",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to (for navigate action)",
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector (for click, fill, extract actions)",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to fill (for fill action)",
                    },
                    "screenshot_path": {
                        "type": "string",
                        "description": "Path to save screenshot (for screenshot action)",
                    },
                },
                "required": ["action"],
            },
        }

class DocumentQueryTool(BaseTool):
    """Document processing and querying tool."""
    
    name = "document_query"
    description = "Query and extract text from documents (PDF, HTML, TXT)"
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
    
    async def execute(
        self,
        action: str,
        document_path: str,
        questions: Optional[list[str]] = None,
    ) -> ToolResult:
        """Execute document action.
        
        Args:
            action: One of 'query', 'extract_text'
            document_path: Path to document (relative to workspace or absolute)
            questions: List of questions to answer (for query action)
        """
        try:
            # Resolve path
            path = Path(document_path)
            if not path.is_absolute():
                path = self.workspace_path / document_path
            
            if not path.exists():
                return ToolResult(success=False, output=None, error=f"Document not found: {document_path}")
            
            # Get file extension
            ext = path.suffix.lower()
            
            if action == "extract_text":
                text = await self._extract_text(path, ext)
                return ToolResult(
                    success=True,
                    output=text,
                    metadata={"path": str(path), "format": ext}
                )
            
            elif action == "query":
                if not questions:
                    return ToolResult(success=False, output=None, error="Questions required for query action")
                
                text = await self._extract_text(path, ext)
                answers = await self._answer_questions(text, questions)
                return ToolResult(
                    success=True,
                    output=answers,
                    metadata={"path": str(path), "questions_count": len(questions)}
                )
            
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown action: {action}. Valid actions: query, extract_text"
                )
                
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    async def _extract_text(self, path: Path, ext: str) -> str:
        """Extract text from document based on format."""
        if ext == ".txt":
            async with aiofiles.open(path, "r") as f:
                return await f.read()
        
        elif ext == ".html":
            async with aiofiles.open(path, "r") as f:
                html_content = await f.read()
            
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, "lxml")
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                return soup.get_text(separator="\n", strip=True)
            except ImportError:
                # Fallback: simple regex-based extraction
                import re
                text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text
        
        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
                return "\n".join(text_parts)
            except ImportError:
                raise RuntimeError("pypdf not installed. Run: pip install pypdf")
        
        else:
            raise ValueError(f"Unsupported document format: {ext}")
    
    async def _answer_questions(self, text: str, questions: list[str]) -> dict[str, str]:
        """Answer questions based on document text.
        
        This is a simple implementation that searches for relevant sections.
        For production, integrate with an LLM for better answers.
        """
        answers = {}
        text_lower = text.lower()
        
        for question in questions:
            # Simple keyword-based search
            # Extract key terms from question
            words = [w for w in question.lower().split() if len(w) > 3]
            
            # Find sentences containing keywords
            sentences = text.split(".")
            relevant = []
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(word in sentence_lower for word in words):
                    relevant.append(sentence.strip())
            
            if relevant:
                answers[question] = ". ".join(relevant[:3])  # Top 3 relevant sentences
            else:
                answers[question] = "No relevant information found in document."
        
        return answers
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["query", "extract_text"],
                        "description": "Document action to perform",
                    },
                    "document_path": {
                        "type": "string",
                        "description": "Path to the document (PDF, HTML, or TXT)",
                    },
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of questions to answer (for query action)",
                    },
                },
                "required": ["action", "document_path"],
            },
        }

class SearchTool(BaseTool):
    """Web search tool."""
    
    name = "search"
    description = "Search the web and return results"
    
    def __init__(self, workspace_path: Path, timeout: int = 30):
        self.workspace_path = workspace_path
        self.timeout = timeout
    
    async def execute(
        self,
        query: str,
        num_results: int = 5,
    ) -> ToolResult:
        """Execute web search.
        
        Args:
            query: Search query string
            num_results: Number of results to return (default 5)
        """
        try:
            import httpx
            
            # Using DuckDuckGo HTML search (no API key required)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                response.raise_for_status()
            
            # Parse results
            results = self._parse_search_results(response.text, num_results)
            
            return ToolResult(
                success=True,
                output=results,
                metadata={"query": query, "count": len(results)}
            )
            
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    def _parse_search_results(self, html: str, num_results: int) -> list[dict]:
        """Parse search results from HTML response."""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            
            # DuckDuckGo HTML results structure
            for result in soup.select(".result")[:num_results]:
                title_elem = result.select_one(".result__a")
                snippet_elem = result.select_one(".result__snippet")
                url_elem = result.select_one(".result__url")
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    # Get actual URL from redirect link
                    href = title_elem.get("href", "")
                    if "uddg=" in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        url = parsed.get("uddg", [href])[0]
                    else:
                        url = href
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
        except ImportError:
            # Fallback: simple regex parsing
            import re
            # Basic extraction of titles and URLs
            pattern = r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)[:num_results]
            for url, title in matches:
                results.append({"title": title, "url": url, "snippet": ""})
        
        return results
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        }

class MemoryTool(BaseTool):
    """Agent memory operations tool."""
    
    name = "memory"
    description = "Store, retrieve, and delete agent memory entries"
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self._memory_dir = workspace_path / ".agent_memory"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._memory_dir / "index.json"
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure memory index exists."""
        if not self._index_file.exists():
            import json
            self._index_file.write_text(json.dumps({}))
    
    def _load_index(self) -> dict:
        """Load memory index."""
        import json
        return json.loads(self._index_file.read_text())
    
    def _save_index(self, index: dict):
        """Save memory index."""
        import json
        self._index_file.write_text(json.dumps(index, indent=2))
    
    def _key_to_path(self, key: str) -> Path:
        """Convert key to safe filename."""
        # Create safe filename from key using hash
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:50]
        return self._memory_dir / f"{safe_key}_{key_hash}.json"
    
    async def execute(
        self,
        action: str,
        key: str,
        value: Optional[Any] = None,
    ) -> ToolResult:
        """Execute memory action.
        
        Args:
            action: One of 'save', 'load', 'delete'
            key: Memory key identifier
            value: Value to store (for save action)
        """
        try:
            if action == "save":
                if value is None:
                    return ToolResult(success=False, output=None, error="Value required for save action")
                return await self._save(key, value)
            
            elif action == "load":
                return await self._load(key)
            
            elif action == "delete":
                return await self._delete(key)
            
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown action: {action}. Valid actions: save, load, delete"
                )
                
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
    
    async def _save(self, key: str, value: Any) -> ToolResult:
        """Save value to memory."""
        import json
        from datetime import datetime
        
        path = self._key_to_path(key)
        index = self._load_index()
        
        entry = {
            "key": key,
            "value": value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(entry, indent=2))
        
        # Update index
        index[key] = {
            "path": str(path.name),
            "created_at": entry["created_at"],
        }
        self._save_index(index)
        
        return ToolResult(
            success=True,
            output=f"Saved value for key: {key}",
            metadata={"key": key, "path": str(path)}
        )
    
    async def _load(self, key: str) -> ToolResult:
        """Load value from memory."""
        import json
        
        index = self._load_index()
        if key not in index:
            return ToolResult(
                success=False,
                output=None,
                error=f"Key not found in memory: {key}"
            )
        
        path = self._memory_dir / index[key]["path"]
        if not path.exists():
            return ToolResult(
                success=False,
                output=None,
                error=f"Memory file not found for key: {key}"
            )
        
        async with aiofiles.open(path, "r") as f:
            content = await f.read()
        entry = json.loads(content)
        
        return ToolResult(
            success=True,
            output=entry["value"],
            metadata={
                "key": key,
                "created_at": entry.get("created_at"),
                "updated_at": entry.get("updated_at"),
            }
        )
    
    async def _delete(self, key: str) -> ToolResult:
        """Delete value from memory."""
        index = self._load_index()
        if key not in index:
            return ToolResult(
                success=False,
                output=None,
                error=f"Key not found in memory: {key}"
            )
        
        path = self._memory_dir / index[key]["path"]
        if path.exists():
            path.unlink()
        
        del index[key]
        self._save_index(index)
        
        return ToolResult(
            success=True,
            output=f"Deleted key: {key}",
            metadata={"key": key}
        )
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["save", "load", "delete"],
                        "description": "Memory action to perform",
                    },
                    "key": {
                        "type": "string",
                        "description": "Memory key identifier",
                    },
                    "value": {
                        "description": "Value to store (for save action)",
                    },
                },
                "required": ["action", "key"],
            },
        }

class ToolRegistry:
    """Registry of available tools."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self._tools: dict[str, BaseTool] = {}
        # Register default tools
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default tools."""
        self.register(CodeExecutionTool(self.workspace_path))
        self.register(FileReadTool(self.workspace_path))
        self.register(FileWriteTool(self.workspace_path))
        self.register(BrowserTool(self.workspace_path))
        self.register(DocumentQueryTool(self.workspace_path))
        self.register(SearchTool(self.workspace_path))
        self.register(MemoryTool(self.workspace_path))
        self.register(TestRunnerTool(self.workspace_path))
        self.register(CodeValidatorTool(self.workspace_path))
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_schemas(self) -> list[dict]:
        """Get schemas for all registered tools."""
        return [tool.schema() for tool in self._tools.values()]
    
    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool not found: {name}"
            )
        return await tool.execute(**kwargs)

def get_default_registry(workspace_path: Optional[Path] = None) -> ToolRegistry:
    """Get the default tool registry."""
    if workspace_path is None:
        workspace_path = Path.cwd()
    return ToolRegistry(workspace_path)
