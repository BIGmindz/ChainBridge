#!/usr/bin/env python3
"""
ChainIQ ML Training Data Backfill CLI

Usage:
    python -m app.ingest.backfill <input.jsonl> [output.jsonl] [--filter-incomplete]

Arguments:
    input.jsonl           Path to input JSONL file with raw events
    output.jsonl          Path to output file (default: training_rows.jsonl)
    --filter-incomplete   Filter out shipments without delivery events (default: True)
    --include-incomplete  Include incomplete shipments (override filter)

Example:
    python -m app.ingest.backfill logs/events.jsonl data/training_rows.jsonl
    python -m app.ingest.backfill events.jsonl --include-incomplete

PAC-CODY-026: Shadow Mode + Ingestion Alignment Patch
"""

import argparse
import sys
from pathlib import Path

# Ensure the app module is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Main entry point for backfill CLI."""
    parser = argparse.ArgumentParser(
        description="ChainIQ ML Training Data Backfill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m app.ingest.backfill logs/events.jsonl data/training_rows.jsonl
    python -m app.ingest.backfill events.jsonl output.jsonl --include-incomplete
    python -m app.ingest.backfill events.jsonl --filter-incomplete
        """,
    )

    parser.add_argument("input_path", type=str, help="Path to input JSONL file with raw ChainBridge events")

    parser.add_argument(
        "output_path", type=str, nargs="?", default="training_rows.jsonl", help="Path to output JSONL file (default: training_rows.jsonl)"
    )

    parser.add_argument(
        "--filter-incomplete", action="store_true", default=True, help="Filter out shipments without delivery events (default: True)"
    )

    parser.add_argument(
        "--include-incomplete", action="store_true", default=False, help="Include incomplete shipments (override --filter-incomplete)"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Validate input file exists
    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    # Determine filter setting
    filter_incomplete = args.filter_incomplete
    if args.include_incomplete:
        filter_incomplete = False

    # Import and run backfill
    from app.ml.ingestion import backfill_training_data

    try:
        count = backfill_training_data(str(input_path), args.output_path, filter_incomplete=filter_incomplete)

        if count > 0:
            print(f"\n✓ Successfully wrote {count} training rows to {args.output_path}")
            sys.exit(0)
        else:
            print("\n⚠ No training rows generated (check input data)")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: Invalid data: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Backfill failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
