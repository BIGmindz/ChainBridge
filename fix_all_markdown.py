#!/usr/bin/env python3
"""
Radical batch fix for ALL markdown linting issues.
Fixes MD022, MD031, MD032, MD040 in one pass.
"""
import re
from pathlib import Path

def fix_md_content(content):
    """Apply all markdown fixes to content."""
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        curr = lines[i]
        prev = result[-1] if result else ''
        next_line = lines[i+1] if i+1 < len(lines) else ''
        
        # MD022: Headings need blank lines
        if curr.startswith('#'):
            # Add blank before heading if needed
            if result and prev.strip() and not prev.startswith('#'):
                result.append('')
            result.append(curr)
            # Add blank after heading if needed
            if next_line.strip() and not next_line.startswith('#'):
                result.append('')
            i += 1
            continue
        
        # MD031 & MD040: Code fences
        if curr.strip().startswith('```') or curr.strip().startswith('````'):
            is_quad = curr.strip().startswith('````')
            fence_marker = '````' if is_quad else '```'
            
            # Add blank before fence
            if result and prev.strip():
                result.append('')
            
            # MD040: Add language if missing
            fence_line = curr
            if curr.strip() in ['```', '````']:
                # Detect language from next line
                lang = 'text'
                if next_line:
                    nl_lower = next_line.lower()
                    if any(k in nl_lower for k in ['import ', 'def ', 'class ', 'from ', '__']):
                        lang = 'python'
                    elif any(k in nl_lower for k in ['export ', 'const ', 'function', 'npm ', 'yarn ']):
                        lang = 'bash'
                    elif 'apiVersion:' in nl_lower or 'kind:' in nl_lower:
                        lang = 'yaml'
                    elif 'docker' in nl_lower or 'container' in nl_lower:
                        lang = 'yaml'
                fence_line = fence_marker + lang
            
            result.append(fence_line)
            i += 1
            
            # Copy fence content
            while i < len(lines):
                if lines[i].strip().startswith(fence_marker):
                    result.append(lines[i])
                    i += 1
                    # Add blank after closing fence
                    if i < len(lines) and lines[i].strip():
                        result.append('')
                    break
                result.append(lines[i])
                i += 1
            continue
        
        # MD032: Lists need blank lines
        is_list = re.match(r'^[\s]*[-*+][\s]', curr) or re.match(r'^[\s]*\d+\.[\s]', curr)
        prev_is_list = re.match(r'^[\s]*[-*+][\s]', prev) or re.match(r'^[\s]*\d+\.[\s]', prev)
        
        if is_list and not prev_is_list:
            # Start of list - add blank before
            if result and prev.strip():
                result.append('')
        
        result.append(curr)
        
        # Check if list ends
        if is_list:
            next_is_list = re.match(r'^[\s]*[-*+][\s]', next_line) or re.match(r'^[\s]*\d+\.[\s]', next_line)
            if not next_is_list and next_line.strip():
                # List ending, add blank after
                result.append('')
        
        i += 1
    
    return '\n'.join(result)

def main():
    """Fix all markdown files."""
    root = Path('/Users/johnbozza/Multiple-signal-decision-bot')
    fixed = 0
    
    for md_file in root.rglob('*.md'):
        if any(x in str(md_file) for x in ['.venv', 'node_modules', '.git']):
            continue
        
        try:
            original = md_file.read_text(encoding='utf-8')
            fixed_content = fix_md_content(original)
            
            if fixed_content != original:
                md_file.write_text(fixed_content, encoding='utf-8')
                print(f"✓ FIXED: {md_file.relative_to(root)}")
                fixed += 1
            else:
                print(f"  OK: {md_file.relative_to(root)}")
        except Exception as e:
            print(f"✗ ERROR: {md_file.name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed} markdown files")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
