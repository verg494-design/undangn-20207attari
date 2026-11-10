import subprocess
import json
from pathlib import Path

SOURCE = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\pages\invitations")

def test_file_build(component_name):
    """Test if a file can be built when imported in App.jsx"""

    # Create minimal App.jsx with just this component
    app_content = f"""import React from 'react'
import {{ Routes, Route }} from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import HomePage from './pages/HomePage'
import {component_name} from './pages/invitations/{component_name}'

function App() {{
  return (
    <Routes>
      <Route path="/" element={{<MainLayout />}}>
        <Route index element={{<HomePage />}} />
        <Route path="/test" element={{<{component_name} />}} />
      </Route>
    </Routes>
  )
}}

export default App
"""

    appjsx_path = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\App.jsx")
    original = appjsx_path.read_text(encoding="utf-8")

    appjsx_path.write_text(app_content, encoding="utf-8")

    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=r"D:\ATTARIVITATION_REACT_FINAL",
            capture_output=True,
            text=True,
            timeout=30
        )

        success = result.returncode == 0
        error = result.stderr if not success else None

    except Exception as e:
        success = False
        error = str(e)
    finally:
        # Restore original
        appjsx_path.write_text(original, encoding="utf-8")

    return success, error[:500] if error else None

def main():
    print("=" * 60)
    print("TESTING INDIVIDUAL FILE BUILDS")
    print("=" * 60)

    jsx_files = list(SOURCE.glob("*.jsx"))
    jsx_files = [f for f in jsx_files if "venv" not in f.name.lower()]

    # Test first 10 files as sample
    test_files = jsx_files[:10]

    working = []
    broken = []

    for file in test_files:
        component_name = file.stem
        print(f"\nTesting {component_name}...")

        success, error = test_file_build(component_name)

        if success:
            working.append(component_name)
            print(f"  [OK] {component_name}")
        else:
            broken.append({"file": component_name, "error": error})
            print(f"  [FAIL] {component_name}")
            print(f"  Error: {error}")

    results = {
        "tested": len(test_files),
        "working": len(working),
        "broken": len(broken),
        "working_files": working,
        "broken_files": broken
    }

    with open(r"D:\ATTARIVITATION_REACT_FINAL\PHASE2_BUILD_TEST.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n" + "=" * 60)
    print(f"RESULTS: {len(working)} working, {len(broken)} broken")
    print(f"Saved to PHASE2_BUILD_TEST.json")
    print("=" * 60)

if __name__ == "__main__":
    main()
