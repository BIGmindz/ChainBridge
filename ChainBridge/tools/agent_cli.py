"""
ChainBridge Agent CLI

Command-line interface for inspecting and managing AI agent configurations.
Provides quick access to agent metadata, prompts, and system information.

Usage:
    python -m tools.agent_cli list
    python -m tools.agent_cli show FRONTEND_SONNY
    python -m tools.agent_cli validate
    python -m tools.agent_cli dump-json agents_export.json
"""

import argparse
import logging
from typing import Optional

from tools.agent_loader import (
    dump_all_agents_to_json,
    list_agents,
    load_agent,
)
from tools.agent_validate import get_validation_results

logger = logging.getLogger(__name__)


def cmd_list(args: argparse.Namespace) -> int:  # noqa: ARG001
    """List all available agent roles.

    Args:
        args: Parsed command-line arguments (unused, kept for consistency).

    Returns:
        0 on success, 1 on failure.
    """
    roles = list_agents()

    if not roles:
        print("No agents found.")
        return 1

    print(f"\nAvailable Agents ({len(roles)} total):\n")
    for i, role in enumerate(roles, 1):
        print(f"  {i:2d}. {role}")

    print()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Show details for a specific agent role.

    Args:
        args: Parsed command-line arguments (includes 'role_name').

    Returns:
        0 on success, 1 if agent not found.
    """
    role_name = args.role_name
    agent = load_agent(role_name)

    if agent is None:
        print(f"Error: Agent '{role_name}' not found.\n")
        print("Use 'python -m tools.agent_cli list' to see available agents.")
        return 1

    print(f"\n{'='*70}")
    print(f"Agent: {role_name}")
    print(f"{'='*70}\n")

    # System prompt
    print("SYSTEM PROMPT (first 400 chars):")
    print("-" * 70)
    prompt_preview = agent.system_prompt[:400]
    if len(agent.system_prompt) > 400:
        prompt_preview += "... [truncated]"
    print(prompt_preview)
    print()

    # Stats
    print("STATISTICS:")
    print(f"  System Prompt:     {len(agent.system_prompt)} chars")
    print(f"  Onboarding Prompt: {len(agent.onboarding_prompt)} chars")
    print(f"  Knowledge Scope:   {len(agent.knowledge_scope)} chars")
    print(f"  Checklist:         {len(agent.checklist)} chars")
    print()

    return 0


def cmd_validate(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Validate all agent configurations and print a summary.

    Args:
        args: Parsed command-line arguments (unused, kept for consistency).

    Returns:
        0 if all agents are valid, 1 otherwise.
    """
    # Suppress logging from validation to keep output clean
    logging.getLogger("tools.agent_validate").setLevel(logging.CRITICAL)

    valid_count, total_count, invalid_roles = get_validation_results()

    if total_count == 0:
        print("No agents found.\n")
        return 1

    print(f"\nValidation Results: {valid_count}/{total_count} agents valid\n")

    if invalid_roles:
        print(f"Invalid agents: {', '.join(invalid_roles)}\n")
        return 1

    print("All agents are valid ✓\n")
    return 0


def cmd_dump_json(args: argparse.Namespace) -> int:
    """Export all agents to JSON format.

    Args:
        args: Parsed command-line arguments (includes optional 'output_path').

    Returns:
        0 on success, 1 on failure.
    """
    output_path: Optional[str] = args.output_path

    try:
        result = dump_all_agents_to_json(output_path)

        if output_path:
            print(f"Exported agents to: {output_path}")
        else:
            # Print to stdout
            print(result)

        return 0
    except Exception as e:
        logger.error("Failed to export agents: %s", e)
        return 1


def main() -> int:
    """Main CLI entry point.

    Returns:
        0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="agent_cli",
        description="ChainBridge Agent CLI — Manage and inspect AI agent configurations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.agent_cli list
    List all available agent roles

  python -m tools.agent_cli show FRONTEND_SONNY
    Show details for FRONTEND_SONNY

  python -m tools.agent_cli validate
    Validate all agents and show summary

  python -m tools.agent_cli dump-json agents.json
    Export all agents to JSON file

  python -m tools.agent_cli dump-json
    Print all agents as JSON to stdout
        """,
    )

    subparsers = parser.add_subparsers(
        title="Commands",
        description="Available commands",
        dest="command",
        help="Subcommand to execute",
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all available agent roles",
    )
    list_parser.set_defaults(func=cmd_list)

    # Show command
    show_parser = subparsers.add_parser(
        "show",
        help="Show details for a specific agent",
    )
    show_parser.add_argument(
        "role_name",
        help="Agent role name (e.g., FRONTEND_SONNY)",
    )
    show_parser.set_defaults(func=cmd_show)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate all agent configurations",
    )
    validate_parser.set_defaults(func=cmd_validate)

    # Dump-json command
    dump_parser = subparsers.add_parser(
        "dump-json",
        help="Export all agents to JSON",
    )
    dump_parser.add_argument(
        "output_path",
        nargs="?",
        default=None,
        help="Output file path (default: print to stdout)",
    )
    dump_parser.set_defaults(func=cmd_dump_json)

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    # Execute command
    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
