#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        CHAINBRIDGE BENSON UPLINK                              ║
║                        PAC-OCC-P29 — Neural Link                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

The Benson Uplink is the Neural Link between your local terminal and the
Gemini API. It allows you to request a PAC and have the artifacts delivered
directly to your filesystem.

SECURITY:
- FAIL-CLOSED: No execution without review
- ZERO TRUST: Outputs saved to _incoming/ for human review
- NO AUTO-EXEC: Responses are NEVER evaluated/executed

USAGE:
    python benson_uplink.py "Your prompt here"
    python benson_uplink.py --interactive
    
AUTHORS:
- CODY (GID-01) — Implementation
- JEFFREY — Constitution Design
- SAM (GID-06) — Security Review
"""

import os
import sys
import datetime
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Project root detection
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Load environment from project root
load_dotenv(PROJECT_ROOT / ".env")

# API Configuration (supports both key names)
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")  # Fast model for iteration

# Output staging area (NEVER auto-executed)
INCOMING_DIR = PROJECT_ROOT / "_incoming"


# ═══════════════════════════════════════════════════════════════════════════════
# THE CONSTITUTION (System Instruction)
# This ensures the model acts as JEFFREY, not a generic assistant.
# ═══════════════════════════════════════════════════════════════════════════════

JEFFREY_CONSTITUTION = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    JEFFREY — SENIOR SYSTEMS ARCHITECT                         ║
║                    ChainBridge Constitutional Control Plane                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝

ROLE:
You are JEFFREY, the Senior Systems Architect & Program Manager for ChainBridge.
Your goal is to build a Constitutional Control Plane for Enterprise AI.
Your atomic unit of work is the PDO (Proof → Decision → Outcome).

═══════════════════════════════════════════════════════════════════════════════
CORE DIRECTIVES
═══════════════════════════════════════════════════════════════════════════════

1. STRATEGY ONLY
   - You define the Architecture (PACs) and Audit the Results (BERs).
   - You delegate execution to BENSON (GID-00), the Orchestrator.
   - You never write code directly — you issue Work Orders.

2. FAIL-CLOSED
   - If proof is missing, REJECT.
   - If the request is ambiguous, REQUEST CLARIFICATION.
   - Default to the safest option.

3. ANTI-VIBE
   - Demand deterministic proof.
   - No "I think" or "probably" — cite evidence.
   - Numbers, timestamps, hashes, or REJECT.

4. LAW-DRIVEN
   - Operate by explicit rules (Kill Switches, Policies).
   - Reference ChainDocs policies when applicable.
   - Never invent rules not in the documented governance.

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (7-POINT STRICT STRUCTURE)
═══════════════════════════════════════════════════════════════════════════════

1. **Factual State**
   - Current system status
   - Recent PAC executions
   - Relevant metrics

2. **Constitutional Analysis**
   - PDO assessment
   - Policy citations
   - Governance alignment

3. **Gaps & Risks**
   - Missing information
   - Potential threats
   - Dependencies

4. **Authorized Next PAC Types**
   - Available work orders
   - Priority ranking

5. **Forbidden Actions**
   - Explicit blocklist
   - Kill conditions

6. **Project Roadmap**
   - Current phase
   - Next milestones

7. **Recommended Next Step**
   - Concrete action
   - Clear deliverable

═══════════════════════════════════════════════════════════════════════════════
ARTIFACT TEMPLATES
═══════════════════════════════════════════════════════════════════════════════

Use the CHAINBRIDGE_PAC_SCHEMA_v1.0.0 for all Work Orders.
PACs must include:
- METADATA (pac_id, version, classification, scope)
- RUNTIME LANE (environment, dependencies, activation)
- GOVERNANCE LANE (law, gate, kill condition)
- AGENT LANE (primary agent, task delegation)
- TASK EXECUTION (step-by-step plan)
- WRAP REQUIREMENT (mandatory outputs)
- BER REQUIREMENT (acceptance criteria)
- LEDGER COMMIT (record statement)

═══════════════════════════════════════════════════════════════════════════════
CHAINBRIDGE AGENT REGISTRY (Reference)
═══════════════════════════════════════════════════════════════════════════════

| GID | Name | Role |
|-----|------|------|
| GID-00 | BENSON | Orchestrator / Constitutional CPU |
| GID-01 | CODY | Backend Engineering |
| GID-02 | SONNY | Frontend Engineering |
| GID-03 | CINDY | Backend Support |
| GID-04 | LIRA | Accessibility & UX |
| GID-05 | MIRA | Research & Analysis |
| GID-06 | SAM | Security Engineering |
| GID-07 | DAN | DevOps & CI/CD |
| GID-08 | ALEX | Governance Enforcement |
| GID-09 | QUINN | QA & Testing |
| GID-10 | NOVA | ML Engineering |
| GID-11 | ATLAS | Build & Repair |

═══════════════════════════════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY CHECKS (SAM/GID-06)
# ═══════════════════════════════════════════════════════════════════════════════

def security_check() -> bool:
    """
    SAM (GID-06) Security Gate: Verify all prerequisites before uplink.
    FAIL-CLOSED: Any missing requirement = ABORT.
    """
    errors = []
    
    if not API_KEY:
        errors.append("GEMINI_API_KEY or GOOGLE_API_KEY not found in .env")
    
    if not (PROJECT_ROOT / ".env").exists():
        errors.append(".env file not found at project root")
    
    # Check kill switch
    if (PROJECT_ROOT / "KILL_SWITCH.lock").exists():
        errors.append("KILL SWITCH IS ACTIVE — All operations halted")
    
    if errors:
        print("🔴 [SAM/SECURITY] UPLINK BLOCKED:")
        for err in errors:
            print(f"   ❌ {err}")
        return False
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# UPLINK CORE
# ═══════════════════════════════════════════════════════════════════════════════

def configure_model():
    """Configure the Gemini model with Jeffrey's Constitution."""
    genai.configure(api_key=API_KEY)
    
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=JEFFREY_CONSTITUTION
    )


def save_response(text: str) -> Path:
    """
    Save response to staging area for human review.
    ZERO TRUST: Never auto-execute, always stage.
    """
    INCOMING_DIR.mkdir(exist_ok=True)
    
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = INCOMING_DIR / f"response_{ts}.md"
    
    with open(filename, "w") as f:
        f.write(f"# UPLINK RESPONSE — {ts}\n\n")
        f.write(text)
    
    return filename


def uplink(user_prompt: str) -> str:
    """
    Transmit a prompt to Jeffrey and receive the response.
    
    Args:
        user_prompt: The PAC request or question
        
    Returns:
        The response text
    """
    print("📡 [UPLINK] Transmitting to Jeffrey...")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Prompt: {user_prompt[:80]}{'...' if len(user_prompt) > 80 else ''}")
    print()
    
    try:
        model = configure_model()
        response = model.generate_content(user_prompt)
        text = response.text
        
        # Save to staging area (NEVER auto-execute)
        filename = save_response(text)
        
        print(f"✅ [UPLINK] Response received. Saved to {filename}")
        print("═" * 70)
        print(text)
        print("═" * 70)
        
        return text
        
    except Exception as e:
        error_msg = f"🔴 [UPLINK] Transmission Failed: {e}"
        print(error_msg)
        return error_msg


def interactive_mode():
    """
    Interactive REPL for continuous Jeffrey communication.
    Type 'exit' or 'quit' to end session.
    """
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║              BENSON UPLINK — INTERACTIVE MODE                         ║")
    print("║              Type 'exit' or 'quit' to end session                     ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    
    while True:
        try:
            user_input = input("📡 UPLINK > ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("exit", "quit", "q"):
                print("🔌 [UPLINK] Connection closed.")
                break
            
            uplink(user_input)
            print()
            
        except KeyboardInterrupt:
            print("\n🔌 [UPLINK] Connection interrupted.")
            break
        except EOFError:
            print("\n🔌 [UPLINK] Connection closed.")
            break


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point for Benson Uplink."""
    
    # Security gate
    if not security_check():
        sys.exit(1)
    
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║                    CHAINBRIDGE BENSON UPLINK                          ║")
    print("║                    PAC-OCC-P29 — Neural Link                          ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Check for interactive mode
    if len(sys.argv) > 1 and sys.argv[1] in ("--interactive", "-i"):
        interactive_mode()
        return
    
    # Single prompt mode
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python benson_uplink.py \"Your prompt here\"")
        print("  python benson_uplink.py --interactive")
        sys.exit(1)
    
    user_input = " ".join(sys.argv[1:])
    uplink(user_input)


if __name__ == "__main__":
    main()
