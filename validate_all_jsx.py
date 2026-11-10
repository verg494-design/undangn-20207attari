import subprocess
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SOURCE = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\pages\invitations")

def validate_jsx_file(file_path):
    """Validate a single JSX file using esbuild"""
    component_name = file_path.stem

    # Create a test import file
    test_content = f"""import {{ component_name }} from './pages/invitations/{component_name}'
"""
    test_file = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\temp_test.jsx")
    test_file.write_text(test_content, encoding="utf-8")

    try:
        result = subprocess.run(
            ["npx", "esbuild", "src/temp_test.jsx", "--format=esm"],
            cwd=r"D:\ATTARIVITATION_REACT_FINAL",
            capture_output=True,
            text=True,
            timeout=10
        )

        test_file.unlink()

        if result.returncode == 0:
            return {"file": component_name, "valid": True, "error": None}
        else:
            # Extract first line of error
            error_line = result.stderr.split('\n')[0] if result.stderr else "Unknown error"
            return {"file": component_name, "valid": False, "error": error_line[:200]}
    except Exception as e:
        test_file.unlink()
        return {"file": component_name, "valid": False, "error": str(e)[:200]}

def main():
    print("=" * 60)
    print("VALIDATING ALL JSX FILES")
    print("=" * 60)

    jsx_files = list(SOURCE.glob("*.jsx"))
    # Skip venv files
    jsx_files = [f for f in jsx_files if "venv" not in f.name.lower()]

    print(f"\nFound {len(jsx_files)} JSX files to validate")

    valid = []
    invalid = []

    # Validate sequentially to avoid overwhelming the system
    for i, file in enumerate(jsx_files):
        result = validate_jsx_file(file)

        if result["valid"]:
            valid.append(result["file"])
            print(f"  [OK] {result['file']}")
        else:
            invalid.append(result)
            print(f"  [FAIL] {result['file']}: {result['error']}")

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(jsx_files)}")

    results = {
        "total": len(jsx_files),
        "valid": len(valid),
        "invalid": len(invalid),
        "valid_files": valid,
        "invalid_files": invalid
    }

    with open(r"D:\ATTARIVITATION_REACT_FINAL\PHASE2_JSX_VALIDATION.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n" + "=" * 60)
    print(f"VALIDATION COMPLETE")
    print(f"Valid: {len(valid)}")
    print(f"Invalid: {len(invalid)}")
    print(f"Results saved to PHASE2_JSX_VALIDATION.json")
    print("=" * 60)

if __name__ == "__main__":
    main()
