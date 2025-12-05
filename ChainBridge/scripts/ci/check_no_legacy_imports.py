from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPES = ["api", "core", "chainiq-service", "chainpay-service"]


def main() -> int:
    bad: list[tuple[Path, str]] = []

    for scope in SCOPES:
        base = ROOT / scope
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("import legacy") or stripped.startswith("from legacy"):
                    bad.append((path, line))

    if bad:
        print("ERROR: Forbidden imports from `legacy` detected:")
        for path, line in bad:
            print(f" - {path}: {line.strip()}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
