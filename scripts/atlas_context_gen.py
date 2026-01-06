#!/usr/bin/env python3
"""
ATLAS CONTEXT GENERATOR (GID-11)
PAC-OCC-P15: Deep Context Ingestion

Scans the ChainBridge repository and generates a comprehensive
context document for Jeffrey's architectural review.

SECURITY: Excludes .env, secrets, credentials
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = PROJECT_ROOT / "docs" / "CHAINBRIDGE_CONTEXT_v1.md"

# Directories to scan
SCAN_DIRS = ["src", "api", "core", "docs/governance", "docs/architecture", "docs/pdo"]

# File extensions to include
INCLUDE_EXTENSIONS = {".py", ".md", ".json"}

# Patterns to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    "node_modules",
    ".venv",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    ".egg-info",
    "*.pyc",
    ".env",
    "secrets",
    "credentials",
]

# Files to explicitly exclude (security)
EXCLUDE_FILES = {
    ".env",
    ".env.dev",
    ".env.local",
    ".env.production",
    "secrets.json",
    "credentials.json",
}

# Priority files to include first
PRIORITY_FILES = [
    "api/server.py",
    "api/occ_benson.py",
    "src/core/orchestrator.py",
    "src/core/tools.py",
    "docs/governance/AGENT_REGISTRY.json",
    "pytest.ini",
    "requirements.txt",
    "Makefile",
]


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded."""
    path_str = str(path)
    
    # Check filename exclusions
    if path.name in EXCLUDE_FILES:
        return True
    
    # Check pattern exclusions
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    
    return False


def get_file_content(filepath: Path, max_lines: int = 500) -> str:
    """Read file content with line limit for large files."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        
        if len(lines) > max_lines:
            truncated = "\n".join(lines[:max_lines])
            return f"{truncated}\n\n... [TRUNCATED: {len(lines) - max_lines} more lines] ..."
        
        return content
    except Exception as e:
        return f"[ERROR READING FILE: {e}]"


def generate_context():
    """Generate the context document."""
    output_lines = []
    file_count = 0
    total_bytes = 0
    
    # Header
    output_lines.append("# CHAINBRIDGE DEEP CONTEXT v1.0")
    output_lines.append("")
    output_lines.append("═" * 80)
    output_lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    output_lines.append(f"Generator: ATLAS (GID-11) via BENSON (GID-00)")
    output_lines.append(f"PAC Reference: PAC-OCC-P15")
    output_lines.append("═" * 80)
    output_lines.append("")
    output_lines.append("## TABLE OF CONTENTS")
    output_lines.append("")
    
    collected_files = []
    
    # Collect priority files first
    output_lines.append("### Priority Files (Core Architecture)")
    for rel_path in PRIORITY_FILES:
        filepath = PROJECT_ROOT / rel_path
        if filepath.exists() and not should_exclude(filepath):
            collected_files.append(("PRIORITY", rel_path, filepath))
            output_lines.append(f"- [{rel_path}](#{rel_path.replace('/', '-').replace('.', '-')})")
    
    output_lines.append("")
    output_lines.append("### Scanned Directories")
    
    # Scan directories
    for scan_dir in SCAN_DIRS:
        dir_path = PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue
        
        output_lines.append(f"- `{scan_dir}/`")
        
        for filepath in sorted(dir_path.rglob("*")):
            if not filepath.is_file():
                continue
            if filepath.suffix not in INCLUDE_EXTENSIONS:
                continue
            if should_exclude(filepath):
                continue
            
            rel_path = str(filepath.relative_to(PROJECT_ROOT))
            
            # Skip if already in priority
            if rel_path in PRIORITY_FILES:
                continue
            
            collected_files.append(("SCAN", rel_path, filepath))
    
    output_lines.append("")
    output_lines.append("─" * 80)
    output_lines.append("")
    output_lines.append("## FILE CONTENTS")
    output_lines.append("")
    
    # Generate content for each file
    for category, rel_path, filepath in collected_files:
        anchor = rel_path.replace("/", "-").replace(".", "-")
        
        output_lines.append(f"### {rel_path}")
        output_lines.append(f"<a name=\"{anchor}\"></a>")
        output_lines.append("")
        output_lines.append(f"**Category:** {category}")
        output_lines.append(f"**Size:** {filepath.stat().st_size} bytes")
        output_lines.append("")
        
        # Determine code fence language
        ext = filepath.suffix
        lang = {".py": "python", ".json": "json", ".md": "markdown"}.get(ext, "")
        
        content = get_file_content(filepath)
        total_bytes += len(content)
        file_count += 1
        
        if ext == ".md":
            # For markdown, use blockquote to avoid nesting issues
            output_lines.append("<details>")
            output_lines.append(f"<summary>Click to expand {rel_path}</summary>")
            output_lines.append("")
            output_lines.append(f"```{lang}")
            output_lines.append(content)
            output_lines.append("```")
            output_lines.append("</details>")
        else:
            output_lines.append(f"```{lang}")
            output_lines.append(content)
            output_lines.append("```")
        
        output_lines.append("")
        output_lines.append("─" * 40)
        output_lines.append("")
    
    # Footer stats
    output_lines.append("")
    output_lines.append("═" * 80)
    output_lines.append("## GENERATION STATS")
    output_lines.append("")
    output_lines.append(f"- **Files Processed:** {file_count}")
    output_lines.append(f"- **Total Content Size:** {total_bytes:,} bytes ({total_bytes / 1024:.1f} KB)")
    output_lines.append(f"- **Output File:** {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")
    output_lines.append("")
    output_lines.append("═" * 80)
    output_lines.append("END OF CONTEXT DOCUMENT")
    output_lines.append("═" * 80)
    
    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    final_content = "\n".join(output_lines)
    OUTPUT_FILE.write_text(final_content, encoding="utf-8")
    
    return file_count, len(final_content), OUTPUT_FILE


if __name__ == "__main__":
    print("🔵 ATLAS (GID-11): Starting Deep Context Generation...")
    print("=" * 60)
    
    file_count, output_size, output_path = generate_context()
    
    print(f"✅ Files Processed: {file_count}")
    print(f"✅ Output Size: {output_size:,} bytes ({output_size / 1024:.1f} KB)")
    print(f"✅ Output Path: {output_path}")
    print("=" * 60)
    print("🟢 ATLAS: Context Generation Complete")
