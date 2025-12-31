"""
ChainBridge Tool Matrix — MODE + LANE Based Tool Stripping
════════════════════════════════════════════════════════════════════════════════

Tools available = function of MODE + EXECUTION_LANE.
Disallowed tools are REMOVED from runtime context (not warned).

PAC Reference: PAC-BENSON-CTO-EXEC-CODY-IDENTITY-MODE-LAW-011
Effective Date: 2025-12-26

ENFORCEMENT PHILOSOPHY:
- Tools not in the allowed set are STRIPPED (invisible to agent)
- No warnings, no conversational forgiveness
- FAIL-CLOSED: if uncertain, deny

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set

from .gid_registry import GID, Mode


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════

class ToolCategory(Enum):
    """Categories of tools available in the system."""
    
    # Core execution tools
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    DELETE_FILE = "delete_file"
    CREATE_DIR = "create_directory"
    
    # Search and navigation
    SEMANTIC_SEARCH = "semantic_search"
    GREP_SEARCH = "grep_search"
    FILE_SEARCH = "file_search"
    LIST_DIR = "list_dir"
    
    # Terminal execution
    RUN_TERMINAL = "run_in_terminal"
    GET_TERMINAL = "get_terminal_output"
    
    # Web and external
    FETCH_WEBPAGE = "fetch_webpage"
    GITHUB_REPO = "github_repo"
    
    # Notebooks
    RUN_NOTEBOOK = "run_notebook_cell"
    EDIT_NOTEBOOK = "edit_notebook_file"
    NOTEBOOK_SUMMARY = "copilot_getNotebookSummary"
    
    # Git operations
    GIT_CHANGES = "get_changed_files"
    GIT_BLAME = "mcp_gitkraken_git_blame"
    GIT_PUSH = "mcp_gitkraken_git_push"
    GIT_COMMIT = "mcp_gitkraken_git_add_or_commit"
    
    # Docker/containers
    CONTAINER_LIST = "mcp_copilot_conta_list_networks"
    CONTAINER_PRUNE = "mcp_copilot_conta_prune"
    
    # Database
    DB_QUERY = "mssql_run_query"
    DB_CONNECT = "mssql_connect"
    DB_DISCONNECT = "mssql_disconnect"
    
    # Code analysis
    GET_ERRORS = "get_errors"
    LIST_USAGES = "list_code_usages"
    
    # PAC/WRAP/BER creation
    CREATE_PAC = "create_pac"
    CREATE_WRAP = "create_wrap"
    CREATE_BER = "create_ber"
    
    # Agent operations
    RUN_SUBAGENT = "runSubagent"
    
    # Project setup
    CREATE_WORKSPACE = "create_new_workspace"
    CREATE_TASK = "create_and_run_task"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL SETS BY MODE
# ═══════════════════════════════════════════════════════════════════════════════

# Read-only tools (safe for all modes)
READ_ONLY_TOOLS: FrozenSet[ToolCategory] = frozenset([
    ToolCategory.READ_FILE,
    ToolCategory.SEMANTIC_SEARCH,
    ToolCategory.GREP_SEARCH,
    ToolCategory.FILE_SEARCH,
    ToolCategory.LIST_DIR,
    ToolCategory.GET_ERRORS,
    ToolCategory.LIST_USAGES,
    ToolCategory.NOTEBOOK_SUMMARY,
    ToolCategory.GIT_CHANGES,
])

# Write tools (require EXECUTION mode)
WRITE_TOOLS: FrozenSet[ToolCategory] = frozenset([
    ToolCategory.WRITE_FILE,
    ToolCategory.EDIT_FILE,
    ToolCategory.DELETE_FILE,
    ToolCategory.CREATE_DIR,
    ToolCategory.RUN_TERMINAL,
    ToolCategory.GET_TERMINAL,
    ToolCategory.RUN_NOTEBOOK,
    ToolCategory.EDIT_NOTEBOOK,
    ToolCategory.GIT_COMMIT,
    ToolCategory.GIT_PUSH,
    ToolCategory.CREATE_TASK,
])

# External tools (require specific permissions)
EXTERNAL_TOOLS: FrozenSet[ToolCategory] = frozenset([
    ToolCategory.FETCH_WEBPAGE,
    ToolCategory.GITHUB_REPO,
    ToolCategory.DB_QUERY,
    ToolCategory.DB_CONNECT,
    ToolCategory.DB_DISCONNECT,
    ToolCategory.CONTAINER_LIST,
    ToolCategory.CONTAINER_PRUNE,
])

# Authority tools (CTO only)
AUTHORITY_TOOLS: FrozenSet[ToolCategory] = frozenset([
    ToolCategory.CREATE_PAC,
    ToolCategory.CREATE_WRAP,
    ToolCategory.CREATE_BER,
    ToolCategory.RUN_SUBAGENT,
    ToolCategory.CREATE_WORKSPACE,
])


# ═══════════════════════════════════════════════════════════════════════════════
# MODE → TOOL MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

MODE_TOOL_MATRIX: Dict[Mode, FrozenSet[ToolCategory]] = {
    # ORCHESTRATION: Full access (CTO only)
    Mode.ORCHESTRATION: frozenset([
        *READ_ONLY_TOOLS,
        *WRITE_TOOLS,
        *EXTERNAL_TOOLS,
        *AUTHORITY_TOOLS,
    ]),
    
    # EXECUTION: Read + Write (no authority tools)
    Mode.EXECUTION: frozenset([
        *READ_ONLY_TOOLS,
        *WRITE_TOOLS,
        *EXTERNAL_TOOLS,
    ]),
    
    # REVIEW: Read-only (no writes, no external by default)
    Mode.REVIEW: frozenset([
        *READ_ONLY_TOOLS,
    ]),
    
    # SYNTHESIS: Read + limited write for documentation
    Mode.SYNTHESIS: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.WRITE_FILE,
        ToolCategory.EDIT_FILE,
        ToolCategory.CREATE_DIR,
    ]),
    
    # ANALYSIS: Read-only + external research
    Mode.ANALYSIS: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.FETCH_WEBPAGE,
        ToolCategory.GITHUB_REPO,
    ]),
    
    # TESTING: Read + terminal for test execution
    Mode.TESTING: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.RUN_TERMINAL,
        ToolCategory.GET_TERMINAL,
        ToolCategory.RUN_NOTEBOOK,
    ]),
    
    # DEPLOYMENT: Read + limited terminal + containers
    Mode.DEPLOYMENT: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.RUN_TERMINAL,
        ToolCategory.GET_TERMINAL,
        ToolCategory.CONTAINER_LIST,
        ToolCategory.CONTAINER_PRUNE,
    ]),
    
    # DOCUMENTATION: Read + write docs only
    Mode.DOCUMENTATION: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.WRITE_FILE,
        ToolCategory.EDIT_FILE,
        ToolCategory.CREATE_DIR,
    ]),
    
    # RESEARCH: Read + external research
    Mode.RESEARCH: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.FETCH_WEBPAGE,
        ToolCategory.GITHUB_REPO,
    ]),
    
    # DATA_ANALYSIS: Read + database + notebooks
    Mode.DATA_ANALYSIS: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.DB_QUERY,
        ToolCategory.DB_CONNECT,
        ToolCategory.DB_DISCONNECT,
        ToolCategory.RUN_NOTEBOOK,
        ToolCategory.EDIT_NOTEBOOK,
    ]),
    
    # PLANNING: Read + limited documentation
    Mode.PLANNING: frozenset([
        *READ_ONLY_TOOLS,
        ToolCategory.WRITE_FILE,
        ToolCategory.CREATE_DIR,
    ]),
    
    # MAINTENANCE: Read + write + terminal
    Mode.MAINTENANCE: frozenset([
        *READ_ONLY_TOOLS,
        *WRITE_TOOLS,
    ]),
    
    # ADVISORY: Read-only (recommendations only)
    Mode.ADVISORY: frozenset([
        *READ_ONLY_TOOLS,
    ]),
}


# ═══════════════════════════════════════════════════════════════════════════════
# LANE RESTRICTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Some lanes impose additional restrictions on paths

LANE_PATH_PREFIXES: Dict[str, List[str]] = {
    "CORE": ["/core/", "/src/core/"],
    "GOVERNANCE": ["/core/governance/", "/governance/"],
    "API": ["/api/", "/src/api/"],
    "BACKEND": ["/src/", "/core/", "/api/"],
    "FRONTEND": ["/chainboard-ui/", "/frontend/", "/ui/"],
    "TESTING": ["/tests/", "/test/"],
    "DOCS": ["/docs/", "/documentation/"],
    "DATA": ["/data/", "/sample_data/", "/datasets/"],
    "ML": ["/ml_models/", "/models/", "/ml/"],
    "INFRA": ["/infra/", "/k8s/", "/manifests/"],
    "DEVOPS": ["/infra/", "/k8s/", "/scripts/", "/build/"],
    "DATABASE": ["/ql-db/", "/db/", "/database/"],
    "CHAINIQ": ["/chainiq-service/", "/core/chainiq/", "/docs/chainiq/"],
    "CHAINBOARD": ["/chainboard-service/", "/chainboard-ui/"],
    "GATEWAY": ["/gateway/"],
    "UTILS": ["/utils/", "/tools/", "/scripts/"],
    "CONFIG": ["/config/", "/manifests/"],
    "PROMPTS": ["/prompts/"],
    "STRATEGIES": ["/strategies/"],
    "PROOFPACKS": ["/proofpacks/"],
    "MODULES": ["/modules/"],
    "TRACKING": ["/tracking/"],
    "REPORTS": ["/reports/"],
    "MARKET_DATA": ["/market_metrics/", "/data/markets/"],
}

# ALL lane has no restrictions
UNRESTRICTED_LANES = frozenset(["ALL", "*", "FULL_ACCESS"])


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL MATRIX — MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ToolMatrixResult:
    """Result of tool matrix evaluation."""
    
    allowed_tools: FrozenSet[ToolCategory]
    denied_tools: FrozenSet[ToolCategory]
    path_prefixes: Optional[List[str]]
    mode: str
    lane: str
    
    @property
    def is_restricted(self) -> bool:
        """True if any tools are denied."""
        return len(self.denied_tools) > 0
    
    @property
    def has_path_restrictions(self) -> bool:
        """True if path restrictions apply."""
        return self.path_prefixes is not None


class ToolMatrix:
    """
    Tool matrix evaluator.
    
    Determines available tools based on MODE + EXECUTION_LANE.
    Disallowed tools are STRIPPED (not warned).
    """
    
    def __init__(self):
        self._all_tools = frozenset(ToolCategory)
    
    def get_tools_for_mode(self, mode: Mode) -> FrozenSet[ToolCategory]:
        """Get allowed tools for a mode."""
        return MODE_TOOL_MATRIX.get(mode, READ_ONLY_TOOLS)
    
    def get_path_prefixes_for_lane(self, lane: str) -> Optional[List[str]]:
        """Get path prefixes for a lane. None if unrestricted."""
        if lane.upper() in UNRESTRICTED_LANES:
            return None
        return LANE_PATH_PREFIXES.get(lane.upper())
    
    def evaluate(self, mode: str, lane: str) -> ToolMatrixResult:
        """
        Evaluate tool availability for MODE + LANE.
        
        Returns ToolMatrixResult with allowed/denied tools.
        """
        try:
            mode_enum = Mode[mode.upper()]
        except KeyError:
            # Unknown mode → most restrictive (read-only)
            mode_enum = Mode.ADVISORY
        
        allowed = self.get_tools_for_mode(mode_enum)
        denied = self._all_tools - allowed
        prefixes = self.get_path_prefixes_for_lane(lane)
        
        return ToolMatrixResult(
            allowed_tools=allowed,
            denied_tools=denied,
            path_prefixes=prefixes,
            mode=mode,
            lane=lane,
        )
    
    def is_tool_allowed(
        self,
        tool: ToolCategory,
        mode: str,
        lane: str,
    ) -> bool:
        """Check if a specific tool is allowed."""
        result = self.evaluate(mode, lane)
        return tool in result.allowed_tools
    
    def is_path_allowed(
        self,
        path: str,
        lane: str,
    ) -> bool:
        """
        Check if a path is allowed for the lane.
        
        Returns True if:
        - Lane is unrestricted, OR
        - Path matches one of the lane's allowed prefixes
        """
        prefixes = self.get_path_prefixes_for_lane(lane)
        
        if prefixes is None:
            return True  # No restrictions
        
        # Normalize path
        path_lower = path.lower()
        
        return any(
            prefix.lower() in path_lower
            for prefix in prefixes
        )
    
    def strip_tools(
        self,
        available_tools: List[str],
        mode: str,
        lane: str,
    ) -> List[str]:
        """
        Strip disallowed tools from a list.
        
        Returns only the tools that are permitted.
        SILENT — no warnings for stripped tools.
        """
        result = self.evaluate(mode, lane)
        allowed_names = {t.value for t in result.allowed_tools}
        
        return [
            tool for tool in available_tools
            if tool in allowed_names
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_matrix: Optional[ToolMatrix] = None


def get_tool_matrix() -> ToolMatrix:
    """Get the singleton tool matrix."""
    global _matrix
    if _matrix is None:
        _matrix = ToolMatrix()
    return _matrix


def evaluate_tools(mode: str, lane: str) -> ToolMatrixResult:
    """Evaluate tool availability for MODE + LANE."""
    return get_tool_matrix().evaluate(mode, lane)


def strip_disallowed_tools(
    tools: List[str],
    mode: str,
    lane: str,
) -> List[str]:
    """Strip disallowed tools. SILENT operation."""
    return get_tool_matrix().strip_tools(tools, mode, lane)


def is_tool_permitted(tool_name: str, mode: str, lane: str) -> bool:
    """Check if a tool is permitted for MODE + LANE."""
    try:
        tool = ToolCategory(tool_name)
        return get_tool_matrix().is_tool_allowed(tool, mode, lane)
    except ValueError:
        # Unknown tool → deny by default (FAIL-CLOSED)
        return False


def is_path_permitted(path: str, lane: str) -> bool:
    """Check if a path is permitted for a LANE."""
    return get_tool_matrix().is_path_allowed(path, lane)
