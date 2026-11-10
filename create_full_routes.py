import json
from pathlib import Path

# Read conversion report
report_file = Path(r"D:\ATTARIVITATION_REACT_FINAL\CONVERSION_REPORT.json")
with open(report_file, encoding="utf-8") as f:
    report = json.load(f)

# Filter out venv files
routes = [r for r in report["routes"] if "venv" not in r["component_name"].lower()]

# Generate lazy-loaded imports
lazy_imports = []
for route in routes:
    lazy_imports.append(f'const {route["component_name"]} = lazy(() => import("./pages/invitations/{route["component_name"]}"))')

# Generate route elements with Suspense
route_elements = []
for route in routes:
    route_elements.append(f'        <Route path="{route["path"]}" element={{<Suspense fallback={{<div>Loading...</div>}}><{route["component_name"]} /></Suspense>}} />')

app_content = f"""import React, {{ lazy, Suspense }} from 'react'
import {{ Routes, Route }} from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import HomePage from './pages/HomePage'

{chr(10).join(lazy_imports)}

function App() {{
  return (
    <Routes>
      <Route path="/" element={{<MainLayout />}}>
        <Route index element={{<HomePage />}} />
{chr(10).join(route_elements)}
      </Route>
    </Routes>
  )
}}

export default App
"""

appjsx_path = Path(r"D:\ATTARIVITATION_REACT_FINAL\src\App.jsx")
appjsx_path.write_text(app_content, encoding="utf-8")

print(f"Created App.jsx with {len(route_elements)} lazy-loaded routes")
print(f"Total imports: {len(lazy_imports)}")
