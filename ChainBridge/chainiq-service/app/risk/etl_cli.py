"""Local ETL tool for moving risk LOG_EVENT JSON lines into the metrics tables.

Not production-grade; for local dev and experimentation.
"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session, sessionmaker

from app.risk.db_models import Base, RiskEvaluation
from app.risk.ingest import risk_log_to_orm
from app.risk.metrics_compute import compute_and_persist_risk_metrics

# Default local SQLite DB for dev
DEFAULT_DB_URL = "sqlite:///./chainiq_risk_metrics.db"


def get_engine(db_url: str):
    """Create a SQLAlchemy engine."""
    return create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})


def get_session_factory(db_url: str):
    """Create a session factory."""
    engine = get_engine(db_url)
    # Ensure tables exist for local dev
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def process_log_file(file_path: Path, session: Session) -> tuple[int, int]:
    """Read a log file and ingest events into the DB.

    Returns:
        tuple: (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0

    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Handle "LOG_EVENT: " prefix if present
            if line.startswith("LOG_EVENT: "):
                json_str = line.split("LOG_EVENT: ", 1)[1]
            else:
                # Try parsing the whole line if it looks like JSON
                json_str = line

            try:
                data = json.loads(json_str)

                # Only process RISK_EVALUATION events
                if data.get("event_type") != "RISK_EVALUATION":
                    continue

                orm_obj = risk_log_to_orm(data)

                # Check for duplicates (simple check by evaluation_id)
                existing = session.query(RiskEvaluation).filter_by(evaluation_id=orm_obj.evaluation_id).first()
                if existing:
                    # Skip or update? For now, skip.
                    continue

                session.add(orm_obj)
                success_count += 1

                # Commit in batches or every row? For CLI, every row is safer for now,
                # or commit at end. Let's commit every 100.
                if success_count % 100 == 0:
                    session.commit()

            except (json.JSONDecodeError, KeyError, ValueError):
                # print(f"Failed to process line: {e}", file=sys.stderr)
                failure_count += 1
                continue
            except Exception as e:
                print(f"Unexpected error: {e}", file=sys.stderr)
                failure_count += 1
                continue

    session.commit()
    return success_count, failure_count


def load_log_file(args):
    """Command handler for load-log-file."""
    path = Path(args.path)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    SessionLocal = get_session_factory(args.db_url)
    session = SessionLocal()

    try:
        print(f"Loading logs from {path} into {args.db_url}...")
        success, failures = process_log_file(path, session)
        print(f"Done. Loaded {success} evaluations ({failures} failures/skipped).")
    finally:
        session.close()


def show_latest(args):
    """Command handler for show-latest."""
    SessionLocal = get_session_factory(args.db_url)
    session = SessionLocal()

    try:
        evals = session.query(RiskEvaluation).order_by(desc(RiskEvaluation.timestamp)).limit(args.limit).all()

        if not evals:
            print("No evaluations found.")
            return

        # Simple table output
        header = f"{'ID':<38} | {'SHIPMENT':<15} | {'SCORE':<5} | {'BAND':<8} | {'TIMESTAMP'}"
        print("-" * len(header))
        print(header)
        print("-" * len(header))

        for e in evals:
            ts_str = e.timestamp.isoformat() if e.timestamp else "N/A"
            print(f"{e.evaluation_id:<38} | {e.shipment_id:<15} | {e.risk_score:<5} | {e.risk_band:<8} | {ts_str}")

    finally:
        session.close()


def compute_metrics(args):
    """Command handler for compute-metrics."""
    SessionLocal = get_session_factory(args.db_url)
    session = SessionLocal()

    try:
        model_version = args.model_version if args.model_version else None
        window_days = args.window_days if args.window_days else None

        result = compute_and_persist_risk_metrics(
            session,
            model_version=model_version,
            window_days=window_days,
        )

        if result is None:
            print("No evaluations found for given filters. No metrics computed.")
            return

        print(f"\nComputed metrics for model_version={result.model_version}")
        print("-" * 50)
        print(f"Eval count:              {result.eval_count}")
        print(f"Avg score:               {result.avg_score:.1f}")
        print(f"Critical Incident Recall:{result.critical_incident_recall:.2f}")
        print(f"High Risk Precision:     {result.high_risk_precision:.2f}")
        print(f"Ops Workload %:          {result.ops_workload_percent:.1f}")
        print(f"Loss Value Coverage:     {result.loss_value_coverage_pct:.2f}")
        print(f"Calibration Monotonic:   {bool(result.calibration_monotonic)}")
        print(f"Calibration Ratio:       {result.calibration_ratio_high_vs_low:.2f}")
        print("-" * 50)

        if result.fail_messages:
            print("Failures:")
            for msg in result.fail_messages:
                print(f"  - {msg}")

        if result.warning_messages:
            print("Warnings:")
            for msg in result.warning_messages:
                print(f"  - {msg}")

        if not result.fail_messages and not result.warning_messages:
            print("✅ No failures or warnings.")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="ChainIQ Risk Metrics ETL CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # load-log-file
    load_parser = subparsers.add_parser("load-log-file", help="Load LOG_EVENT lines from a file")
    load_parser.add_argument("--path", required=True, help="Path to log file")
    load_parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="Database URL")
    load_parser.set_defaults(func=load_log_file)

    # show-latest
    show_parser = subparsers.add_parser("show-latest", help="Show latest risk evaluations")
    show_parser.add_argument("--limit", type=int, default=10, help="Number of rows to show")
    show_parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="Database URL")
    show_parser.set_defaults(func=show_latest)

    # compute-metrics
    metrics_parser = subparsers.add_parser("compute-metrics", help="Compute aggregate metrics from evaluations")
    metrics_parser.add_argument("--model-version", default=None, help="Filter by model version")
    metrics_parser.add_argument("--window-days", type=int, default=None, help="Lookback window in days")
    metrics_parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="Database URL")
    metrics_parser.set_defaults(func=compute_metrics)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
