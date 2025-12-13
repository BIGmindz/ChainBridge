#!/usr/bin/env python3
"""
ChainIQ CLI - Command Line Interface

Provides utility commands for ChainIQ operations, debugging, and analysis.
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
CHAINIQ_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(CHAINIQ_ROOT))


def shadow_stats():
    """Display shadow mode statistics."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.analysis.shadow_diff import compute_shadow_statistics
        from app.core.config import settings

        # Get database URL
        db_url = settings.database_url or os.getenv("DATABASE_URL")

        if not db_url:
            print("ERROR: DATABASE_URL not configured")
            print("Set via .env file or environment variable")
            sys.exit(1)

        # Create session
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Compute statistics
            stats = compute_shadow_statistics(session)

            if not stats:
                print("No shadow mode events found")
                return

            # Pretty print statistics
            print("\n" + "=" * 60)
            print("SHADOW MODE STATISTICS")
            print("=" * 60)
            print(f"\nTotal Events: {stats['count']}")
            print("\nDelta Metrics:")
            print(f"  Mean:   {stats['mean_delta']:.4f}")
            print(f"  Median: {stats['median_delta']:.4f}")
            print(f"  Std:    {stats['std_delta']:.4f}")
            print(f"  P50:    {stats['p50_delta']:.4f}")
            print(f"  P95:    {stats['p95_delta']:.4f}")
            print(f"  P99:    {stats['p99_delta']:.4f}")
            print(f"  Max:    {stats['max_delta']:.4f}")

            if stats["drift_flag"]:
                print("\n⚠️  WARNING: High drift detected (P95 > 0.25)")
            else:
                print("\n✓ Drift within acceptable range")

            # Per-corridor breakdown
            if "by_corridor" in stats and stats["by_corridor"]:
                print("\nPer-Corridor Breakdown:")
                for corridor, corridor_stats in stats["by_corridor"].items():
                    print(
                        f"  {corridor:8s}: {corridor_stats['count']:4d} events, "
                        f"mean={corridor_stats['mean_delta']:.4f}, "
                        f"p95={corridor_stats['p95_delta']:.4f}"
                    )

            print("\n" + "=" * 60)

            # Also export as JSON for programmatic use
            print("\nJSON Output:")
            print(json.dumps(stats, indent=2))

        finally:
            session.close()

    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("Install required packages: pip install sqlalchemy psycopg2-binary numpy")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def shadow_drift():
    """Analyze model drift."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.analysis.shadow_diff import analyze_model_drift
        from app.core.config import settings

        db_url = settings.database_url or os.getenv("DATABASE_URL")

        if not db_url:
            print("ERROR: DATABASE_URL not configured")
            sys.exit(1)

        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Default to 24 hour lookback
            lookback = int(sys.argv[2]) if len(sys.argv) > 2 else 24

            print(f"\nAnalyzing drift (lookback: {lookback} hours)...\n")

            drift = analyze_model_drift(session, lookback_hours=lookback)

            print("=" * 60)
            print("MODEL DRIFT ANALYSIS")
            print("=" * 60)
            print(json.dumps(drift, indent=2))

            if drift.get("drift_detected"):
                print("\n⚠️  DRIFT DETECTED: Real model behavior has shifted significantly")
            else:
                print("\n✓ No significant drift detected")

            print("=" * 60)

        finally:
            session.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def help_text():
    """Display help information."""
    print(
        """
ChainIQ CLI - Command Line Interface

Usage:
  python -m app.cli <command> [args]

Commands:
  shadow-stats              Display shadow mode statistics
  shadow-drift [hours]      Analyze model drift (default: 24 hours)
  # shadow-corridors [hours]  Analyze all corridors (default: 24 hours)
  # shadow-corridor <name>    Analyze specific corridor (e.g., US-CN)
  # shadow-deltas <corridor>  Show top scoring discrepancies for corridor
  # shadow-trend <corridor>   Show time-series trend for corridor
  help                      Show this help message

Examples:
  python -m app.cli shadow-stats
  python -m app.cli shadow-drift 48
  # python -m app.cli shadow-corridors 24
  # python -m app.cli shadow-corridor US-CN
  # python -m app.cli shadow-deltas US-CN
  # python -m app.cli shadow-trend US-CN

Environment:
  DATABASE_URL    PostgreSQL connection URL (required for shadow commands)

Note: Run from chainiq-service directory with proper PYTHONPATH
"""
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        help_text()
        sys.exit(0)

    command = sys.argv[1]

    if command == "shadow-stats":
        shadow_stats()
    elif command == "shadow-drift":
        shadow_drift()
    # elif command == "shadow-corridors":
    #     shadow_corridors()
    # elif command == "shadow-corridor":
    #     shadow_corridor()
    # elif command == "shadow-deltas":
    #     shadow_deltas()
    # elif command == "shadow-trend":
    #     shadow_trend()
    elif command == "help":
        help_text()
    else:
        print(f"Unknown command: {command}")
        print("Run 'python -m app.cli help' for usage information")
        sys.exit(1)
