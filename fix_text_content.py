import re
from pathlib import Path

SOURCE = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\pages\invitations")

def fix_text_content(content: str) -> str:
    """Fix text content that contains angle brackets"""

    # Fix <3, <33, etc. in text by wrapping in curly braces if not already in JSX
    # Pattern: text followed by <3 or <33 not part of a tag
    content = re.sub(r'([a-zA-Z\s])<3', r'\1{"<3"}', content)
    content = re.sub(r'([a-zA-Z\s])<33', r'\1{"<33"}', content)
    content = re.sub(r'([a-zA-Z\s])<333', r'\1{"<333"}', content)

    # Fix other common text patterns with angle brackets
    content = re.sub(r'(\s)<(\d+)', r'\1{"<\2"}', content)

    return content

def main():
    print("=" * 60)
    print("FIXING TEXT CONTENT WITH ANGLE BRACKETS")
    print("=" * 60)

    jsx_files = list(SOURCE.glob("*.jsx"))
    jsx_files = [f for f in jsx_files if "venv" not in f.name.lower()]

    fixed_count = 0
    for file in jsx_files:
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            original = content

            content = fix_text_content(content)

            if content != original:
                file.write_text(content, encoding="utf-8")
                fixed_count += 1
                print(f"  Fixed: {file.name}")
        except Exception as e:
            print(f"  Error: {file.name} - {e}")

    print(f"\nFixed {fixed_count} files")
    print("=" * 60)

if __name__ == "__main__":
    main()
