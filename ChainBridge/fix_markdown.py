#!/usr/bin/env python3
"""
Batch fix all Markdown linting issues (MD022, MD031, MD032, MD040).
"""
import re
import sys
from pathlib import Path


def fix_markdown_file(filepath):
    """Fix all common markdown linting issues."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        lines = content.split("\n")
        fixed_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # MD022: Headings need blank lines before/after
            if line.startswith("#"):
                # Add blank before if needed
                if i > 0 and fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append("")
                fixed_lines.append(line)
                # Add blank after if needed
                if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith("#"):
                    fixed_lines.append("")
                i += 1
                continue

            # MD031: Code fences need blank lines
            if line.strip().startswith("```"):
                # Add blank before fence
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append("")

                # MD040: Add language to fence if missing
                fence_line = line
                if line.strip() == "```" or line.strip() == "````":
                    # Detect language from context
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].lower()
                        if "import " in next_line or "def " in next_line or "class " in next_line:
                            fence_line = line.replace("```", "```python", 1).replace("````", "````python", 1)
                        elif "export" in next_line or "const " in next_line or "npm " in next_line:
                            fence_line = line.replace("```", "```bash", 1).replace("````", "````bash", 1)
                        elif "- [ ]" in next_line or "- [x]" in next_line:
                            fence_line = line.replace("```", "```text", 1).replace("````", "````text", 1)
                        elif "apiVersion:" in next_line or "kind:" in next_line:
                            fence_line = line.replace("```", "```yaml", 1).replace("````", "````yaml", 1)
                        else:
                            fence_line = line.replace("```", "```text", 1).replace("````", "````text", 1)

                fixed_lines.append(fence_line)
                i += 1

                # Copy content until closing fence
                while i < len(lines):
                    if lines[i].strip().startswith("```"):
                        fixed_lines.append(lines[i])
                        i += 1
                        # Add blank after closing fence
                        if i < len(lines) and lines[i].strip():
                            fixed_lines.append("")
                        break
                    fixed_lines.append(lines[i])
                    i += 1
                continue

            # MD032: Lists need blank lines before/after
            if re.match(r"^[\s]*[-*\d]+\.?\s+", line):
                # Start of list - add blank before
                if fixed_lines and fixed_lines[-1].strip() and not re.match(r"^[\s]*[-*\d]+\.?\s+", fixed_lines[-1]):
                    fixed_lines.append("")
                fixed_lines.append(line)
                i += 1
                # Continue through list
                while i < len(lines) and (re.match(r"^[\s]*[-*\d]+\.?\s+", lines[i]) or not lines[i].strip()):
                    fixed_lines.append(lines[i])
                    i += 1
                # Add blank after list
                if i < len(lines) and lines[i].strip():
                    fixed_lines.append("")
                continue

            fixed_lines.append(line)
            i += 1

        # Write if changed
        new_content = "\n".join(fixed_lines)
        if new_content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        return False

    except Exception as e:
        print(f"Error fixing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    """Fix all markdown files in repository."""
    repo_root = Path(__file__).parent
    md_files = list(repo_root.rglob("*.md"))

    fixed_count = 0
    for md_file in md_files:
        if ".venv" in str(md_file) or "node_modules" in str(md_file):
            continue
        print(f"Fixing {md_file.name}...", end=" ")
        if fix_markdown_file(md_file):
            print("✓ FIXED")
            fixed_count += 1
        else:
            print("✓ OK")

    print(f"\nFixed {fixed_count}/{len(md_files)} files")


if __name__ == "__main__":
    main()
