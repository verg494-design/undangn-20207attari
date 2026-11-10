import os
import json
import shutil
from pathlib import Path
from urllib.parse import unquote

# ==========================================
# KONFIGURASI
# ==========================================

BACKUP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BACKUP_DIR.parent / "ATTARIVITATION_REACT"

EXCLUDE = {
    "venv",
    ".git",
    "node_modules",
    "__pycache__",
    "ATTARIVITATION_REACT"
}

# ==========================================
# DETEKSI FILE HTML
# ==========================================

print("\n=== ATTARIVITATION HTML TO REACT ===")

html_files = []

for file in BACKUP_DIR.rglob("*"):
    if not file.is_file():
        continue

    if any(part in EXCLUDE for part in file.parts):
        continue

    if file.suffix.lower() in [".html", ".htm"]:
        html_files.append(file)

if not html_files:
    print("Tidak ditemukan file HTML.")
    print("Pastikan hasil backup crawler berada di folder ini.")
    raise SystemExit(1)

print(f"Ditemukan {len(html_files)} halaman HTML.")

# ==========================================
# PERSIAPAN FOLDER
# ==========================================

if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)

PUBLIC_DIR = OUTPUT_DIR / "public" / "backup"
SRC_DIR = OUTPUT_DIR / "src"

PUBLIC_DIR.mkdir(parents=True)
SRC_DIR.mkdir(parents=True)

# ==========================================
# SALIN HASIL BACKUP
# ==========================================

print("\nMenyalin file backup...")

for item in BACKUP_DIR.iterdir():

    if item.name in EXCLUDE:
        continue

    if item.name == OUTPUT_DIR.name:
        continue

    destination = PUBLIC_DIR / item.name

    try:
        if item.is_dir():
            shutil.copytree(
                item,
                destination,
                ignore=shutil.ignore_patterns(
                    "venv",
                    "node_modules",
                    ".git",
                    "__pycache__"
                ),
                dirs_exist_ok=True
            )
        else:
            shutil.copy2(item, destination)

    except Exception as error:
        print(f"Gagal menyalin {item.name}: {error}")

# ==========================================
# MEMBUAT ROUTE
# ==========================================

routes = []

for file in html_files:

    relative = file.relative_to(BACKUP_DIR)

    relative_url = relative.as_posix()

    parts = list(relative.parts)

    # Hilangkan folder pages jika ada
    if parts and parts[0].lower() in ["pages", "html", "website"]:
        parts = parts[1:]

    route_path = "/" + "/".join(parts)

    if route_path.lower().endswith((".html", ".htm")):
        route_path = route_path.rsplit(".", 1)[0]

    if route_path.endswith("/index"):
        route_path = route_path[:-5]

    if route_path == "":
        route_path = "/"

    if route_path == "/index":
        route_path = "/"

    iframe_url = "/backup/" + relative_url

    routes.append({
        "path": route_path,
        "file": iframe_url,
        "title": file.stem.replace("-", " ").replace("_", " ").title()
    })

# Prioritaskan halaman utama
routes.sort(
    key=lambda x: (
        x["path"] != "/",
        len(x["path"])
    )
)

# Hilangkan route duplikat
unique_routes = {}
for route in routes:
    unique_routes.setdefault(route["path"], route)

routes = list(unique_routes.values())

with open(
    SRC_DIR / "routes.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(routes, f, ensure_ascii=False, indent=2)

# ==========================================
# PACKAGE JSON
# ==========================================

package_json = {
    "name": "attarivitation-react",
    "private": True,
    "version": "1.0.0",
    "type": "module",
    "scripts": {
        "dev": "vite --host 0.0.0.0",
        "build": "vite build",
        "preview": "vite preview"
    },
    "dependencies": {
        "@vitejs/plugin-react": "latest",
        "vite": "latest",
        "react": "latest",
        "react-dom": "latest",
        "react-router-dom": "latest",
        "lucide-react": "latest"
    },
    "devDependencies": {
        "typescript": "latest"
    }
}

with open(
    OUTPUT_DIR / "package.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(package_json, f, indent=2)

# ==========================================
# VITE CONFIG
# ==========================================

(OUTPUT_DIR / "vite.config.ts").write_text(
    """
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true
  }
})
""",
    encoding="utf-8"
)

# ==========================================
# INDEX HTML
# ==========================================

(OUTPUT_DIR / "index.html").write_text(
    """
<!doctype html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="theme-color" content="#ffffff" />
  <title>Attarivitation</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
""",
    encoding="utf-8"
)

# ==========================================
# MAIN TSX
# ==========================================

(SRC_DIR / "main.tsx").write_text(
    """
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './style.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
""",
    encoding="utf-8"
)

# ==========================================
# APP TSX
# ==========================================

(SRC_DIR / "App.tsx").write_text(
    """
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import routes from './routes.json'

type Page = {
  path: string
  file: string
  title: string
}

const pages = routes as Page[]

export default function App() {
  const location = useLocation()
  const [frameKey, setFrameKey] = useState(0)

  const currentPath = decodeURIComponent(location.pathname)

  const page =
    pages.find(item => item.path === currentPath) ||
    pages.find(item => item.path === currentPath.replace(/\\/$/, '')) ||
    pages.find(item => item.path === '/') ||
    pages[0]

  useEffect(() => {
    setFrameKey(value => value + 1)
  }, [location.pathname, location.search])

  if (!page) {
    return <div>Halaman tidak ditemukan.</div>
  }

  const iframeUrl = page.file + location.search

  return (
    <main className="site-container">
      <iframe
        key={frameKey}
        src={iframeUrl}
        title={page.title}
        className="site-frame"
        allow="autoplay; fullscreen; clipboard-write"
        allowFullScreen
      />
    </main>
  )
}
""",
    encoding="utf-8"
)

# ==========================================
# CSS
# ==========================================

(SRC_DIR / "style.css").write_text(
    """
* {
  box-sizing: border-box;
}

html, body, #root {
  margin: 0;
  padding: 0;
  width: 100%;
  min-height: 100%;
}

body {
  overflow: hidden;
}

.site-container {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.site-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: none;
  background: white;
}
""",
    encoding="utf-8"
)

# ==========================================
# ROUTE REPORT
# ==========================================

with open(
    OUTPUT_DIR / "ROUTES.txt",
    "w",
    encoding="utf-8"
) as f:
    for route in routes:
        f.write(
            f"{route['path']} -> {route['file']}\n"
        )

# ==========================================
# README
# ==========================================

(OUTPUT_DIR / "README.txt").write_text(
    """
ATTARIVITATION REACT

Cara menjalankan:

1. Install Node.js versi LTS.
2. Buka terminal pada folder proyek.
3. Jalankan:

   npm install
   npm run dev

4. Buka alamat yang ditampilkan Vite.

Build production:

   npm run build

CATATAN:
Ini merupakan konversi awal berbasis arsip HTML.
Fitur WordPress/PHP/plugin dan database belum dikonversi
menjadi komponen React atau backend.
""",
    encoding="utf-8"
)

# ==========================================
# SELESAI
# ==========================================

print("\n================================")
print("KONVERSI SELESAI")
print("================================")
print(f"Halaman ditemukan : {len(html_files)}")
print(f"Route dibuat      : {len(routes)}")
print(f"Folder hasil      : {OUTPUT_DIR}")
print("\nLangkah selanjutnya:")
print(f"cd {OUTPUT_DIR}")
print("npm install")
print("npm run dev")