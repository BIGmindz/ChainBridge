#!/usr/bin/env python3
"""
ChainIQ v0.1 - Retrospective Pilot CLI

Command-line tool for running retrospective pilots on customer data.
Used by sales/ops to generate pilot reports from historical shipment CSVs.

Usage:
    python -m app.cli_retrospective_pilot pilot_data.csv --tenant ACME-Corp
    python -m app.cli_retrospective_pilot pilot_data.csv --tenant ACME-Corp --output report.md

Author: Maggie (GID-10) - ML & Applied AI Lead
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .evaluation import build_markdown_summary, export_report_to_json, run_retrospective_from_csv


def main(args: argparse.Namespace) -> int:
    """
    Main CLI entrypoint for retrospective pilot.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    csv_path = Path(args.csv_path)

    # Validate input file exists
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    print("🔍 Running retrospective pilot...")
    print(f"   Input:  {csv_path}")
    print(f"   Tenant: {args.tenant}")
    print(f"   Threshold: {args.threshold}")
    print()

    try:
        # Run the pilot
        report = run_retrospective_from_csv(
            csv_path=csv_path,
            tenant_id=args.tenant,
            threshold=args.threshold,
        )

        # Print summary to console
        print("=" * 60)
        print("📊 PILOT RESULTS")
        print("=" * 60)
        print()
        print(f"Total Shipments:     {report.metrics.total_shipments:,}")
        print(f"Bad Events:          {report.metrics.total_bad_events:,} ({report.metrics.bad_event_rate:.1%})")

        if report.metrics.auc_roc is not None:
            print(f"AUC-ROC:             {report.metrics.auc_roc:.3f}")

        if report.metrics.lift_at_top_10pct is not None:
            print(f"Lift @ Top 10%:      {report.metrics.lift_at_top_10pct:.2f}x")

        if report.metrics.capture_rate_top_10pct is not None:
            print(f"Capture Rate:        {report.metrics.capture_rate_top_10pct:.1%}")

        if report.metrics.hypothetical_savings_usd is not None:
            print(f"Hypothetical Savings: ${report.metrics.hypothetical_savings_usd:,.0f}")

        print()
        print("Risk Distribution:")
        for tier, count in report.risk_distribution.items():
            pct = count / report.metrics.total_shipments * 100 if report.metrics.total_shipments > 0 else 0
            bar = "█" * int(pct / 5)
            print(f"  {tier:>8}: {count:5,} ({pct:5.1f}%) {bar}")

        print()

        # Warnings
        if report.notes:
            print("⚠️  Notes:")
            for note in report.notes:
                print(f"   - {note}")
            print()

        # Generate outputs
        if args.output:
            output_path = Path(args.output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = csv_path.parent / f"pilot_report_{args.tenant}_{timestamp}.md"

        # Write markdown report
        markdown = build_markdown_summary(report)
        output_path.write_text(markdown)
        print(f"✅ Markdown report: {output_path}")

        # Write JSON if requested
        if args.json:
            json_path = output_path.with_suffix(".json")
            export_report_to_json(report, json_path)
            print(f"✅ JSON report:     {json_path}")

        print()
        print("Done! Report ready for sales deck. 🚀")

        return 0

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"❌ Validation Error: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"❌ Missing dependency: {e}", file=sys.stderr)
        print("   Install with: pip install pandas scikit-learn", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="chainiq-pilot",
        description="Run ChainIQ retrospective pilot on historical shipment data",
        epilog="Example: python -m app.cli_retrospective_pilot data.csv --tenant ACME-Corp",
    )

    parser.add_argument(
        "csv_path",
        type=str,
        help="Path to CSV file with historical shipment data",
    )

    parser.add_argument(
        "--tenant",
        "-t",
        type=str,
        required=True,
        help="Tenant/customer identifier (e.g., ACME-Corp)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output path for markdown report (default: auto-generated)",
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Also export JSON report alongside markdown",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=60.0,
        help="Risk score threshold for confusion matrix (default: 60)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose error messages",
    )

    return parser


def cli_main() -> None:
    """Entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()
    sys.exit(main(args))


if __name__ == "__main__":
    cli_main()
