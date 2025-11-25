from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STUBS = [
    ROOT / "PROJECT_CHECKLIST.md",
    ROOT / "PROJECT_STATUS_SUMMARY.md",
    ROOT / "M02_QUICK_REFERENCE.md",
]

MAX_LINES = 30  # stub should be tiny
ALLOWED_PHRASES = {
    "MOVED",
    "Canonical version lives at",
    "Do **not** edit this stub",
    "Always update:",
}


def is_stub(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > MAX_LINES:
        return False
    # very light content check
    return any(p in text for p in ALLOWED_PHRASES)


def main() -> int:
    bad: list[Path] = []
    for stub in STUBS:
        if not stub.exists():
            continue
        if not is_stub(stub):
            bad.append(stub)

    if bad:
        print("ERROR: Root docs must be stubs pointing to docs/product/.")
        print("The following files contain non-stub content:")
        for p in bad:
            print(f" - {p}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
