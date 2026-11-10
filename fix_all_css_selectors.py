import re
from pathlib import Path

SOURCE = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\pages\invitations")

def fix_all_css_selectors(content: str) -> str:
    """Remove all CSS class selectors that were left as text content"""

    # Remove any line that is just a CSS class selector (starts with whitespace and dot)
    content = re.sub(r'\n\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*\n', '\n', content)

    # Remove CSS class selectors at end of lines
    content = re.sub(r'\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*$', '', content, flags=re.MULTILINE)

    # Fix double closing tags
    content = re.sub(r'</li>\s*</li>', '</li>', content)
    content = re.sub(r'</div>\s*</div>', '</div>', content)

    # Remove orphaned class selectors after closing tags
    content = re.sub(r'</li>\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*</li>', '</li>', content)
    content = re.sub(r'</div>\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*</div>', '</div>', content)

    # Remove class selectors after closing tags
    content = re.sub(r'</li>\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*<li', '</li>\n<li', content)
    content = re.sub(r'</div>\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*<div', '</div>\n<div', content)

    # Remove class selectors before closing tags
    content = re.sub(r'</li>\s*\.[a-zA-Z_-][a-zA-Z0-9_-]*\s*</ul>', '</li>\n</ul>', content)

    # Clean up multiple empty lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

    return content

def main():
    print("=" * 60)
    print("FIXING ALL CSS SELECTORS IN JSX FILES")
    print("=" * 60)

    jsx_files = list(SOURCE.glob("*.jsx"))
    jsx_files = [f for f in jsx_files if "venv" not in f.name.lower()]

    fixed_count = 0
    for file in jsx_files:
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            original = content

            content = fix_all_css_selectors(content)

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
