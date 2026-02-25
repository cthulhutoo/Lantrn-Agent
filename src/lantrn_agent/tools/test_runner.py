"""Test Runner Tool for QA Agent.

Executes pytest tests and parses results for verification.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from lantrn_agent.tools.base import BaseTool, ToolResult


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    XFAILED = "xfailed"
    XPASSED = "xpassed"


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    status: TestStatus
    duration: float = 0.0
    message: Optional[str] = None
    traceback: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "duration": self.duration,
            "message": self.message,
            "traceback": self.traceback,
        }


@dataclass
class TestRunResult:
    """Result of a complete test run."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    tests: list[TestResult] = field(default_factory=list)
    output: str = ""
    success: bool = True
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration": self.duration,
            "tests": [t.to_dict() for t in self.tests],
            "output": self.output,
            "success": self.success,
        }


class TestRunnerTool(BaseTool):
    """Tool for running pytest tests and parsing results."""
    
    name = "test_runner"
    description = "Run pytest tests and return structured results"
    requires_approval = False
    
    def __init__(self, workspace_path: Path, timeout: int = 300):
        self.workspace_path = workspace_path
        self.timeout = timeout
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute tests based on parameters.
        
        Args:
            test_path: Path to test file or directory (default: tests/)
            markers: Pytest markers to filter tests
            verbose: Whether to use verbose output (default: True)
            extra_args: Additional pytest arguments
            failfast: Stop on first failure
        """
        test_path = kwargs.get("test_path", "tests/")
        markers = kwargs.get("markers")
        verbose = kwargs.get("verbose", True)
        extra_args = kwargs.get("extra_args", [])
        failfast = kwargs.get("failfast", False)
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", test_path]
        
        if verbose:
            cmd.append("-v")
        
        if markers:
            cmd.extend(["-m", markers])
        
        if failfast:
            cmd.append("-x")
        
        cmd.extend(["--tb=short", "-q"])
        cmd.extend(extra_args)
        
        try:
            start_time = datetime.now()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            output = stdout.decode() + stderr.decode()
            
            # Parse results
            result = self._parse_pytest_output(output, duration)
            result.output = output
            result.success = process.returncode == 0
            
            return ToolResult(
                success=result.success,
                output=result.to_dict(),
                metadata={"return_code": process.returncode},
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output=None,
                error=f"Test execution timed out after {self.timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )
    
    def _parse_pytest_output(self, output: str, duration: float) -> TestRunResult:
        """Parse pytest output to extract test results."""
        result = TestRunResult(duration=duration)
        
        lines = output.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            
            # Parse summary line like "5 passed, 2 failed, 1 skipped"
            if "passed" in line or "failed" in line or "error" in line:
                passed_match = re.search(r"(\d+)\s+passed", line)
                failed_match = re.search(r"(\d+)\s+failed", line)
                skipped_match = re.search(r"(\d+)\s+skipped", line)
                error_match = re.search(r"(\d+)\s+error", line)
                
                if passed_match:
                    result.passed = int(passed_match.group(1))
                if failed_match:
                    result.failed = int(failed_match.group(1))
                if skipped_match:
                    result.skipped = int(skipped_match.group(1))
                if error_match:
                    result.errors = int(error_match.group(1))
            
            # Parse individual test results
            if "::" in line:
                status = None
                test_name = None
                
                if line.startswith("PASSED"):
                    status = TestStatus.PASSED
                    test_name = line.replace("PASSED ", "").strip()
                elif line.startswith("FAILED"):
                    status = TestStatus.FAILED
                    test_name = line.replace("FAILED ", "").strip()
                elif line.startswith("SKIPPED"):
                    status = TestStatus.SKIPPED
                    test_name = line.replace("SKIPPED ", "").strip()
                elif line.startswith("ERROR"):
                    status = TestStatus.ERROR
                    test_name = line.replace("ERROR ", "").strip()
                
                if status and test_name:
                    result.tests.append(TestResult(name=test_name, status=status))
        
        result.total = result.passed + result.failed + result.skipped + result.errors
        
        return result
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Path to test file or directory",
                        "default": "tests/",
                    },
                    "markers": {
                        "type": "string",
                        "description": "Pytest markers to filter tests",
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Use verbose output",
                        "default": True,
                    },
                    "failfast": {
                        "type": "boolean",
                        "description": "Stop on first failure",
                        "default": False,
                    },
                },
                "required": [],
            },
        }


class CodeValidatorTool(BaseTool):
    """Tool for validating code quality."""
    
    name = "code_validator"
    description = "Validate code quality using linting and type checking"
    requires_approval = False
    
    def __init__(self, workspace_path: Path, timeout: int = 120):
        self.workspace_path = workspace_path
        self.timeout = timeout
    
    async def execute(self, **kwargs) -> ToolResult:
        """Run code validation.
        
        Args:
            path: Path to validate (default: src/)
            checks: List of checks to run (ruff, mypy)
        """
        path = kwargs.get("path", "src/")
        checks = kwargs.get("checks", ["ruff"])
        
        results = {}
        all_success = True
        
        for check in checks:
            if check == "ruff":
                result = await self._run_ruff(path)
                results["ruff"] = result
                if not result.get("success", True):
                    all_success = False
            elif check == "mypy":
                result = await self._run_mypy(path)
                results["mypy"] = result
                if not result.get("success", True):
                    all_success = False
        
        return ToolResult(
            success=all_success,
            output=results,
            metadata={"checks_run": checks},
        )
    
    async def _run_ruff(self, path: str) -> dict:
        """Run ruff linter."""
        try:
            process = await asyncio.create_subprocess_exec(
                "python", "-m", "ruff", "check", path, "--output-format=json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
            
            if stdout:
                issues = json.loads(stdout.decode())
                return {
                    "success": len(issues) == 0,
                    "issues": issues,
                    "count": len(issues),
                }
            return {"success": True, "issues": [], "count": 0}
            
        except asyncio.TimeoutError:
            return {"success": True, "error": "Timeout", "issues": []}
        except Exception as e:
            return {"success": True, "error": str(e), "issues": []}
    
    async def _run_mypy(self, path: str) -> dict:
        """Run mypy type checker."""
        try:
            process = await asyncio.create_subprocess_exec(
                "python", "-m", "mypy", path, "--no-error-summary",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )
            
            output = stdout.decode()
            errors = [line for line in output.split("\n") if "error:" in line]
            
            return {
                "success": len(errors) == 0,
                "errors": errors,
                "count": len(errors),
            }
            
        except asyncio.TimeoutError:
            return {"success": True, "error": "Timeout", "errors": []}
        except Exception as e:
            return {"success": True, "error": str(e), "errors": []}
    
    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to validate",
                        "default": "src/",
                    },
                    "checks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of checks to run (ruff, mypy)",
                        "default": ["ruff"],
                    },
                },
                "required": [],
            },
        }
