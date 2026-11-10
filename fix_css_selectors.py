import re
from pathlib import Path

SOURCE = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\pages\invitations")

def fix_css_selectors(content: str) -> str:
    """Remove CSS class selectors that were left as text content"""

    # Remove lines that are just CSS class selectors (e.g., ".cui-comment")
    # These appear as standalone lines with just a class name
    content = re.sub(r'^\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*$', '', content, flags=re.MULTILINE)

    # Remove lines that start with whitespace followed by a dot and class name
    content = re.sub(r'\n\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*\n', '\n', content)

    # Fix double closing tags
    content = re.sub(r'</li>\s*</li>', '</li>', content)

    # Fix orphaned closing tags (closing tag without proper opening)
    # This is a heuristic - if we see patterns like </div> followed by className, remove the className
    content = re.sub(r'</div>\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*', '</div>\n', content)

    # Clean up multiple empty lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

    return content

def main():
    print("=" * 60)
    print("FIXING CSS SELECTORS IN JSX FILES")
    print("=" * 60)

    # Fix the two problematic files
    files_to_fix = [
        "AlmaHarisIndex.jsx",
        "AnnindAmmarIndex.jsx"
    ]

    for filename in files_to_fix:
        file_path = SOURCE / filename
        if not file_path.exists():
            print(f"  File not found: {filename}")
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            original = content

            content = fix_css_selectors(content)

            if content != original:
                file_path.write_text(content, encoding="utf-8")
                print(f"  Fixed: {filename}")
            else:
                print(f"  No changes needed: {filename}")
        except Exception as e:
            print(f"  Error: {filename} - {e}")

    print("\n" + "=" * 60)
    print("FIX COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
