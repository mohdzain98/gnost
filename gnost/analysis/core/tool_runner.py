"""
Tool Runner Utility for Code Analysis Tool
Safely executes external analysis tools with timeout and error handling.
"""

import asyncio
import subprocess
import os
import shutil
from gnost.utils.logger import AppLogger
from typing import List, Optional, Dict
from pathlib import Path

logger = AppLogger.get_logger(__name__)


class ToolTimeoutError(Exception):
    """Raised when a tool execution times out."""

    pass


class ToolNotFoundError(Exception):
    """Raised when a required tool is not found."""

    pass


class ToolRunner:
    """Utility class for running external analysis tools safely."""

    def __init__(self):
        """Initialize the tool runner."""
        self.tool_cache = {}
        self._check_tool_availability()

    def _check_tool_availability(self):
        """Check which tools are available on the system."""
        tools_to_check = [
            "pylint",
            "semgrep",
            "gitleaks",
            "radon",
            "mypy",
            "pip-audit",
            "pip-licenses",
            "bandit",
            "safety",
        ]

        for tool in tools_to_check:
            self.tool_cache[tool] = shutil.which(tool) is not None

    def is_tool_available(self, tool_name: str) -> bool:
        """
        Check if a tool is available on the system.

        Args:
            tool_name (str): Name of the tool

        Returns:
            bool: True if tool is available
        """
        return self.tool_cache.get(tool_name, False)

    async def run_tool(
        self,
        tool_name: str,
        args: List[str],
        timeout: int = 300,
        capture_output: bool = True,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run an external tool with proper error handling and timeout.

        Args:
            tool_name (str): Name of the tool to run
            args (List[str]): Arguments to pass to the tool
            timeout (int): Timeout in seconds (default 300)
            capture_output (bool): Whether to capture stdout/stderr
            cwd (Optional[str]): Working directory
            env (Optional[Dict[str, str]]): Environment variables

        Returns:
            subprocess.CompletedProcess: Result of the tool execution

        Raises:
            ToolNotFoundError: If the tool is not available
            ToolTimeoutError: If the tool execution times out
        """
        if not self.is_tool_available(tool_name):
            # Try to install common tools via pip if they're missing
            if tool_name in ["pip-audit", "pip-licenses"]:
                try:
                    self._install_pip_tool(tool_name)
                    self.tool_cache[tool_name] = True
                except Exception:
                    raise ToolNotFoundError(
                        f"Tool '{tool_name}' is not available and could not be installed"
                    )
            else:
                raise ToolNotFoundError(f"Tool '{tool_name}' is not available")

        # Prepare command
        cmd = [tool_name] + args

        # Set up environment
        if env is None:
            env = os.environ.copy()

        # Add common Python paths
        env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":" + str(Path.cwd())

        try:
            stdout_opt = (
                asyncio.subprocess.PIPE
                if capture_output
                else asyncio.subprocess.DEVNULL
            )
            stderr_opt = (
                asyncio.subprocess.PIPE
                if capture_output
                else asyncio.subprocess.DEVNULL
            )
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=stdout_opt,
                stderr=stderr_opt,
                cwd=cwd,
                env=env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                raise ToolTimeoutError(
                    f"Tool '{tool_name}' timed out after {timeout} seconds"
                )

            return subprocess.CompletedProcess(
                cmd,
                returncode=proc.returncode,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
            )

        except FileNotFoundError:
            raise ToolNotFoundError(f"Tool '{tool_name}' was not found in PATH")

        except Exception as e:
            # Return a failed result instead of raising
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="", stderr=str(e)
            )
