"""
CHAINBRIDGE AGENTIC TOOLS (CORE)
PAC-OCC-P11: Tool Binding Infrastructure
PAC-OCC-P22: ChainDocs Policy Engine (Air Canada Shield)
Identity: Benson Execution (GID-00-EXEC)

CONSTRAINT: FAIL-CLOSED — All tools return structured TER (Tool Execution Record)
"""

import hashlib
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


# ═══════════════════════════════════════════════════════════════════
# CHAINDOCS CONFIGURATION (PAC-OCC-P22)
# ═══════════════════════════════════════════════════════════════════

# Policy directory (immutable governance documents)
POLICIES_DIR = Path(__file__).parent.parent.parent / "docs" / "policies"


class ToolStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"


@dataclass
class ToolExecutionRecord:
    """TER: Structured result for every tool execution."""
    tool_name: str
    status: ToolStatus
    output: str
    error: str = ""
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result["status"] = self.status.value
        return result
    
    def __str__(self) -> str:
        return (
            f"[TER] {self.tool_name}\n"
            f"  Status: {self.status.value}\n"
            f"  Output: {self.output[:200]}{'...' if len(self.output) > 200 else ''}\n"
            + (f"  Error: {self.error}\n" if self.error else "")
        )


# ═══════════════════════════════════════════════════════════════════
# TOOL 1: READ_FILE
# ═══════════════════════════════════════════════════════════════════

def read_file(path: str) -> ToolExecutionRecord:
    """
    Read contents of a file. FAIL-CLOSED on error.
    
    Args:
        path: Absolute or relative path to the file.
        
    Returns:
        TER with file contents or error message.
    """
    tool_name = "read_file"
    
    try:
        filepath = Path(path).resolve()
        
        if not filepath.exists():
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILURE,
                output="",
                error=f"File not found: {filepath}"
            )
        
        if not filepath.is_file():
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILURE,
                output="",
                error=f"Path is not a file: {filepath}"
            )
        
        content = filepath.read_text(encoding="utf-8")
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.SUCCESS,
            output=content
        )
        
    except PermissionError:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Permission denied: {path}"
        )
    except Exception as e:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Unexpected error: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════
# TOOL 2: WRITE_FILE
# ═══════════════════════════════════════════════════════════════════

def write_file(path: str, content: str) -> ToolExecutionRecord:
    """
    Write content to a file. Creates directories if needed. FAIL-CLOSED on error.
    
    Args:
        path: Absolute or relative path to the file.
        content: String content to write.
        
    Returns:
        TER with confirmation or error message.
    """
    tool_name = "write_file"
    
    try:
        filepath = Path(path).resolve()
        
        # Create parent directories if they don't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        filepath.write_text(content, encoding="utf-8")
        
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.SUCCESS,
            output=f"File written successfully: {filepath} ({len(content)} bytes)"
        )
        
    except PermissionError:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Permission denied: {path}"
        )
    except Exception as e:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Unexpected error: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════
# TOOL 3: RUN_TERMINAL
# ═══════════════════════════════════════════════════════════════════

# GUARDRAIL: Blocked commands (destructive operations)
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf .",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",  # Fork bomb
    "chmod -R 777 /",
    "chown -R",
]


def run_terminal(command: str, timeout: int = 30) -> ToolExecutionRecord:
    """
    Execute a shell command. FAIL-CLOSED with guardrails.
    
    Args:
        command: Shell command to execute.
        timeout: Maximum execution time in seconds (default 30).
        
    Returns:
        TER with stdout/stderr or error message.
    """
    tool_name = "run_terminal"
    
    # GUARDRAIL: Check for blocked commands
    command_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked in command_lower:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILURE,
                output="",
                error=f"🔴 BLOCKED: Destructive command detected: '{blocked}'"
            )
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.SUCCESS,
                output=output if output else "(no output)",
                error=error if error else ""
            )
        else:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILURE,
                output=output,
                error=f"Exit code {result.returncode}: {error}"
            )
            
    except subprocess.TimeoutExpired:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Command timed out after {timeout} seconds"
        )
    except Exception as e:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Execution error: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════
# TOOL 4: SPAWN_AGENT (PAC-OCC-P17)
# ═══════════════════════════════════════════════════════════════════

def spawn_agent(gid: str, task: str) -> ToolExecutionRecord:
    """
    Spawn a sub-agent by GID to execute a task.
    
    This allows Benson to delegate work to specialized agents.
    
    GOVERNANCE:
    - ALEX (GID-08) Law: "No agent may be spawned without valid GID from Registry."
    - Kill Switch is checked BEFORE spawn.
    
    Args:
        gid: The agent's GID (e.g., "GID-01" for CODY, "GID-11" for ATLAS)
        task: The task description for the sub-agent to execute.
        
    Returns:
        TER with the sub-agent's output or error message.
    """
    tool_name = "spawn_agent"
    
    try:
        # Import here to avoid circular dependency
        from src.core.agents.factory import create_agent, AgentStatus
        
        # Spawn the agent and execute the task
        result = create_agent(gid, task)
        
        if result.status == AgentStatus.COMPLETED:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.SUCCESS,
                output=f"[{result.gid}] {result.name} — COMPLETED\n\n{result.output}",
            )
        elif result.status == AgentStatus.BLOCKED:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILURE,
                output="",
                error=result.error,
            )
        else:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILURE,
                output=result.output,
                error=result.error,
            )
            
    except ImportError as e:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Agent Factory not available: {str(e)}"
        )
    except Exception as e:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Spawn error: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════
# TOOL 5: READ_POLICY (PAC-OCC-P22 — Air Canada Shield)
# ═══════════════════════════════════════════════════════════════════

def read_policy(policy_name: str) -> ToolExecutionRecord:
    """
    Read a ChainDocs policy and return its content + SHA256 hash.
    
    This is the "Air Canada Shield" — agents MUST cite policy hashes
    when making decisions about company rules or procedures.
    
    GOVERNANCE:
    - ALEX (GID-08) Law: "No policy claims without hash citation."
    - Policies are IMMUTABLE. Changes require new version + approval.
    
    Args:
        policy_name: Name of the policy (without .md extension).
                     Example: "PRIMARY_DIRECTIVE"
        
    Returns:
        TER with policy content, hash, and citation format.
    """
    tool_name = "read_policy"
    
    try:
        # Construct policy path
        policy_file = POLICIES_DIR / f"{policy_name}.md"
        
        if not policy_file.exists():
            # List available policies for helpful error
            available = []
            if POLICIES_DIR.exists():
                available = [f.stem for f in POLICIES_DIR.glob("*.md")]
            
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILURE,
                output="",
                error=f"Policy not found: {policy_name}. Available: {available}"
            )
        
        # Read content
        content = policy_file.read_text(encoding="utf-8")
        
        # Compute SHA256 hash
        policy_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        short_hash = policy_hash[:12]  # First 12 chars for citation
        
        # Build output with citation format
        output = (
            f"┌─────────────────────────────────────────────────────────────────┐\n"
            f"│ CHAINDOCS POLICY: {policy_name}\n"
            f"│ HASH: {policy_hash}\n"
            f"│ CITE AS: [{policy_name}:{short_hash}]\n"
            f"└─────────────────────────────────────────────────────────────────┘\n\n"
            f"{content}"
        )
        
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.SUCCESS,
            output=output
        )
        
    except PermissionError:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Permission denied reading policy: {policy_name}"
        )
    except Exception as e:
        return ToolExecutionRecord(
            tool_name=tool_name,
            status=ToolStatus.FAILURE,
            output="",
            error=f"Error reading policy: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════
# TOOL REGISTRY (For Gemini Function Calling)
# ═══════════════════════════════════════════════════════════════════

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "write_file": write_file,
    "run_terminal": run_terminal,
    "spawn_agent": spawn_agent,
    "read_policy": read_policy,  # PAC-OCC-P22: ChainDocs Policy Engine
}


# ═══════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🔵 TOOLS SELF-TEST")
    print("=" * 50)
    
    # Test 1: read_file (missing file)
    print("\n[TEST 1] read_file - missing file")
    result = read_file("/nonexistent/path/file.txt")
    print(result)
    assert result.status == ToolStatus.FAILURE
    
    # Test 2: write_file
    print("\n[TEST 2] write_file - create test file")
    test_path = "/tmp/chainbridge_tool_test.txt"
    result = write_file(test_path, "ChainBridge P11 Test")
    print(result)
    assert result.status == ToolStatus.SUCCESS
    
    # Test 3: read_file (existing file)
    print("\n[TEST 3] read_file - read test file")
    result = read_file(test_path)
    print(result)
    assert result.status == ToolStatus.SUCCESS
    assert "ChainBridge P11 Test" in result.output
    
    # Test 4: run_terminal
    print("\n[TEST 4] run_terminal - echo command")
    result = run_terminal('echo "Hello from Benson"')
    print(result)
    assert result.status == ToolStatus.SUCCESS
    assert "Hello from Benson" in result.output
    
    # Test 5: run_terminal (blocked command)
    print("\n[TEST 5] run_terminal - blocked command guardrail")
    result = run_terminal("rm -rf /")
    print(result)
    assert result.status == ToolStatus.FAILURE
    assert "BLOCKED" in result.error
    
    # Cleanup
    os.remove(test_path)
    
    print("\n" + "=" * 50)
    print("🟢 ALL TOOL TESTS PASSED")
