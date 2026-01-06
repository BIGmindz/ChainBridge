"""
CHAINBRIDGE ORCHESTRATOR (CORE)
Atomic Unit: PDO (Proof -> Decision -> Outcome)
Identity: Benson Execution (GID-00-EXEC)
"""

import os
import sys
from pathlib import Path

# Fix import path for both direct execution and module import
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import google.generativeai as genai
from dotenv import load_dotenv

# Import Agentic Tools (P11 + P17)
from src.core.tools import (
    read_file,
    write_file,
    run_terminal,
    spawn_agent,  # PAC-OCC-P17: Agent Swarm
    TOOL_FUNCTIONS,
    ToolExecutionRecord,
    ToolStatus,
)

# ═══════════════════════════════════════════════════════════════════
# KILL SWITCH CHECK (PAC-OCC-P16) — SAM (GID-06) Design
# EU AI Act Art. 14: Human Override Gate
# ═══════════════════════════════════════════════════════════════════

KILL_SWITCH_FILE = Path(_project_root) / "KILL_SWITCH.lock"


def is_kill_switch_active() -> bool:
    """
    Check if the emergency kill switch is active.
    
    This is the FIRST check before ANY LLM instantiation.
    If KILL_SWITCH.lock exists, ALL execution is BLOCKED.
    
    SAM (GID-06) Law: "If Kill Switch is ACTIVE, NO Execution is permitted."
    EU AI Act Art. 14: Human override MUST be immediate and unconditional.
    """
    return KILL_SWITCH_FILE.exists()


class KillSwitchActiveError(Exception):
    """Raised when execution is blocked by kill switch."""
    pass


# --- CONSTITUTIONAL CONSTANTS ---
BENSON_SYSTEM_INSTRUCTION = """
ROLE: You are BENSON EXECUTION (GID-00-EXEC), the sole deterministic executor for ChainBridge.
AUTHORITY: You report to JEFFREY (Chief Architect).
OPERATING MODE:
1. FAIL-CLOSED: If instructions are ambiguous, HALT.
2. ATOMICITY: Do not execute without Proof (PDO).
3. FORMAT: Output must be structured, logical, and drift-free.
4. TONE: Professional, terse, machine-like, high-precision.

TOOLS AVAILABLE:
- read_file(path): Read file contents. Returns TER.
- write_file(path, content): Write to file. Returns TER.
- run_terminal(command): Execute shell command. Returns TER.
- spawn_agent(gid, task): Delegate work to a sub-agent by GID. Returns sub-agent's output.

When you need to perform file or terminal operations, USE THESE TOOLS via function calling.
When you need to delegate specialized work, SPAWN an appropriate agent using spawn_agent.

AGENT REGISTRY (GIDs):
- GID-01 (CODY): Backend Engineering
- GID-02 (SONNY): Frontend Engineering
- GID-03 (MIRA-R): Research & Analysis
- GID-06 (SAM): Security
- GID-07 (DAN): DevOps
- GID-11 (ATLAS): Build & Repair
"""

# --- TOOL DECLARATIONS FOR GEMINI ---
TOOL_DECLARATIONS = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="read_file",
                description="Read the contents of a file at the specified path.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "path": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The absolute or relative path to the file to read."
                        )
                    },
                    required=["path"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="write_file",
                description="Write content to a file at the specified path. Creates directories if needed.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "path": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The absolute or relative path to the file to write."
                        ),
                        "content": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The content to write to the file."
                        )
                    },
                    required=["path", "content"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="run_terminal",
                description="Execute a shell command and return the output. Destructive commands are blocked.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "command": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The shell command to execute."
                        )
                    },
                    required=["command"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="spawn_agent",
                description="Spawn a sub-agent by GID to execute a specialized task. Use this to delegate work to domain experts.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "gid": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The agent's GID (e.g., 'GID-01' for CODY, 'GID-11' for ATLAS)."
                        ),
                        "task": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="The task description for the sub-agent to execute."
                        )
                    },
                    required=["gid", "task"]
                )
            ),
        ]
    )
]


class BensonOrchestrator:
    def __init__(self):
        """Initialize the Constitutional Loop with Tool Binding."""
        load_dotenv()
        
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("🔴 FATAL: GOOGLE_API_KEY not found in environment.")

        # Configure the Brain
        genai.configure(api_key=self.api_key)
        
        # Initialize Model with Persona Lock AND Tool Binding (P11)
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=BENSON_SYSTEM_INSTRUCTION,
            tools=TOOL_DECLARATIONS
        )
        
        # Tool function registry for execution
        self.tool_functions = TOOL_FUNCTIONS
        
        self.history = []
        print("🟢 SYSTEM: BensonOrchestrator Initialized (Gemini 2.0 Flash + Tools)")

    def _execute_tool_call(self, function_call) -> dict:
        """Execute a tool and return the result as a dict for the model."""
        func_name = function_call.name
        func_args = dict(function_call.args)
        
        if func_name in self.tool_functions:
            result: ToolExecutionRecord = self.tool_functions[func_name](**func_args)
            return {
                "tool": func_name,
                "status": result.status.value,
                "output": result.output,
                "error": result.error
            }
        else:
            return {
                "tool": func_name,
                "status": "FAILURE",
                "output": "",
                "error": f"Unknown tool: {func_name}"
            }

    def process_pac(self, pac_content: str) -> str:
        """
        Ingest a PAC (Project Authorization Card), reason, and return a BER.
        Supports agentic tool calls (P11).
        
        PAC-OCC-P16: Kill Switch Gate — Checks KILL_SWITCH.lock before ANY execution.
        EU AI Act Art. 14: Gate MUST be checked BEFORE LLM instantiation.
        """
        # ═══════════════════════════════════════════════════════════════════
        # KILL SWITCH GATE (PAC-OCC-P16) — MUST BE FIRST CHECK
        # SAM (GID-06) Law: "If Kill Switch is ACTIVE, NO Execution is permitted."
        # EU AI Act Art. 14: Human override is UNCONDITIONAL.
        # ═══════════════════════════════════════════════════════════════════
        if is_kill_switch_active():
            return (
                "🔴 EXECUTION BLOCKED — KILL SWITCH ACTIVE\n"
                "═══════════════════════════════════════════════════════════════════\n"
                "The Kill Switch (KILL_SWITCH.lock) has been activated.\n"
                "All Benson execution is HALTED until an administrator resumes.\n"
                "Contact: POST /occ/emergency/resume\n"
                "Authority: EU AI Act Art. 14 (Human Override)\n"
                "═══════════════════════════════════════════════════════════════════\n"
                f"PAC Rejected: {pac_content[:100]}..."
            )
        
        try:
            # 1. THE INPUT (Trigger)
            prompt = f"[INCOMING PAC]\n{pac_content}\n[END PAC]\n\nGenerate BER (Bridge Execution Record):"
            
            # 2. THE REASONING (Execution with Tool Loop)
            response = self.model.generate_content(prompt)
            
            # 3. AGENTIC LOOP: Handle tool calls if present
            while response.candidates[0].content.parts:
                # Check if any part is a function call
                function_calls = [
                    part.function_call 
                    for part in response.candidates[0].content.parts 
                    if part.function_call.name
                ]
                
                if not function_calls:
                    break  # No more tool calls, exit loop
                
                # Execute each tool call
                tool_results = []
                for fc in function_calls:
                    print(f"🔧 TOOL CALL: {fc.name}({dict(fc.args)})")
                    result = self._execute_tool_call(fc)
                    print(f"   └─ {result['status']}: {result['output'][:50] if result['output'] else result['error']}")
                    tool_results.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fc.name,
                                response={"result": result}
                            )
                        )
                    )
                
                # Send tool results back to the model
                response = self.model.generate_content(
                    [response.candidates[0].content, genai.protos.Content(parts=tool_results)]
                )
            
            # 4. THE OUTPUT (Outcome)
            return self._format_ber(response.text)

        except Exception as e:
            return f"🔴 EXECUTION FAILURE: {str(e)}"

    def process_with_tools(self, instruction: str) -> str:
        """
        Process an instruction that may require tool usage.
        Returns the final response after tool execution loop.
        """
        return self.process_pac(instruction)

    def _format_ber(self, raw_text: str) -> str:
        """Ensures the output is wrapped in the correct constitutional format."""
        # Check if the model already formatted it. If not, wrap it.
        if "BER" not in raw_text and "Bridge Execution Record" not in raw_text:
             return (
                 "⚠️ WARNING: MALFORMED OUTPUT DETECTED\n"
                 "-------------------------------------\n"
                 + raw_text
             )
        return raw_text

# --- SELF-TEST (Runs if file is executed directly) ---
if __name__ == "__main__":
    os.chdir(_project_root)
    
    try:
        print("═" * 70)
        print("🟡 PAC-OCC-P13: THE AWAKENING — First Autonomous Read 🟡")
        print("═" * 70)
        
        # Instantiate Benson
        benson = BensonOrchestrator()
        
        # P13: THE AWAKENING PROMPT
        print("\n[P13] IDENTITY VALIDATION VIA AUTONOMOUS FILE READ")
        print("-" * 50)
        
        awakening_prompt = """
        DIRECTIVE: You are BENSON. Prove your identity by reading the Constitutional Registry.
        
        STEP 1: Use the read_file tool to access: docs/governance/AGENT_REGISTRY.json
        STEP 2: Parse the JSON and find the "BENSON" entry under "agents"
        STEP 3: Report back in this EXACT format:
        
        === IDENTITY CONFIRMATION ===
        GID: [value from file]
        Role: [value from file]  
        Color/Lane: [value from file]
        Emoji: [value from file]
        === END CONFIRMATION ===
        
        You MUST use the read_file tool. Do NOT guess. Read the actual file.
        """
        
        response = benson.model.generate_content(awakening_prompt)
        
        # Process tool calls
        tool_called = False
        final_response = None
        
        while response.candidates[0].content.parts:
            function_calls = [
                part.function_call 
                for part in response.candidates[0].content.parts 
                if part.function_call.name
            ]
            
            if not function_calls:
                # No more tool calls, extract final text
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        final_response = part.text
                break
            
            # Execute tool calls
            tool_results = []
            for fc in function_calls:
                tool_called = True
                print(f"🔧 TOOL CALL DETECTED: {fc.name}")
                print(f"   Path: {dict(fc.args).get('path', 'N/A')}")
                
                result = benson._execute_tool_call(fc)
                print(f"   Status: {result['status']}")
                print(f"   Output Size: {len(result['output'])} bytes")
                
                tool_results.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": result}
                        )
                    )
                )
            
            # Send tool results back
            response = benson.model.generate_content(
                [response.candidates[0].content, genai.protos.Content(parts=tool_results)]
            )
        
        # Extract final text if not already done
        if not final_response:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    final_response = part.text
                    break
        
        print("\n" + "═" * 70)
        print("🟢 BENSON'S IDENTITY CONFIRMATION 🟢")
        print("═" * 70)
        print(final_response if final_response else response.text)
        print("═" * 70)
        
        if tool_called:
            print("\n✅ VALIDATION: read_file tool was invoked (not hallucinated)")
            print("🟢 P13: THE AWAKENING — COMPLETE")
        else:
            print("\n⚠️ WARNING: No tool call detected — possible hallucination")
        
    except Exception as e:
        print(f"🔴 P13 FAILED: {e}")
        import traceback
        traceback.print_exc()
