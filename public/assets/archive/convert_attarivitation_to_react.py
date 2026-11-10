#!/usr/bin/env python3
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import shutil, json, re, hashlib, sys

# Sesuaikan dua path ini dengan folder di komputer Anda.
SOURCE_DIR = Path(r"D:\ATTARIVITATION_BACKUP")
OUTPUT_DIR = Path(r"D:\ATTARIVITATION_REACT_V2")
SKIP = {"venv", ".venv", "node_modules", ".git", "__pycache__",
        "ATTARIVITATION_AUDIT", "ATTARIVITATION_REACT", "ATTARIVITATION_REACT_V2"}

def safe_name(s):
    s = re.sub(r"[^a-zA-Z0-9_]", "_", s)
    return ("Page_" if not s or s[0].isdigit() else "") + s[:85]

def route_for(rel):
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1].lower() == "index":
        parts.pop()
    return "/" + "/".join(re.sub(r"[^a-zA-Z0-9_-]", "-", p).strip("-").lower() for p in parts) if parts else "/"

def external(url):
    return url.startswith(("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:", "#"))

def find_local(url, page):
    raw = unquote(url.split("#")[0].split("?")[0])
    if not raw or external(raw):
        return None
    path = urlparse(raw).path
    candidate = SOURCE_DIR / path.lstrip("/") if path.startswith("/") else page.parent / path
    try:
        candidate = candidate.resolve()
        candidate.relative_to(SOURCE_DIR.resolve())
    except Exception:
        return None
    return candidate if candidate.is_file() else None

def public_url(path):
    return "/archive/" + path.resolve().relative_to(SOURCE_DIR.resolve()).as_posix()

def rewrite_fragment(markup, page, routes):
    soup = BeautifulSoup(markup, "html.parser")
    for tag in soup.find_all(True):
        for attr in ("src", "poster", "data-src", "data-lazy-src", "href"):
            value = tag.get(attr)
            if not value or external(value):
                continue
            target = find_local(value, page)
            if target:
                if attr == "href" and target.suffix.lower() in (".html", ".htm"):
                    rel = target.resolve().relative_to(SOURCE_DIR.resolve()).as_posix()
                    tag[attr] = routes.get(rel, public_url(target))
                else:
                    tag[attr] = public_url(target)
    return str(soup)

def extract_page(path, rel, routes):
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else path.stem
    styles, scripts = [], []
    if soup.head:
        for link in soup.head.find_all("link", href=True):
            if "stylesheet" in " ".join(link.get("rel", [])).lower():
                f = find_local(link["href"], path)
                styles.append({"type":"link", "href":public_url(f) if f else link["href"]})
        for st in soup.head.find_all("style"):
            styles.append({"type":"inline", "content":st.string or st.get_text()})
        for sc in soup.head.find_all("script"):
            src = sc.get("src")
            if src:
                f = find_local(src, path)
                scripts.append({"type":"src", "src":public_url(f) if f else src})
            elif sc.string or sc.get_text(strip=True):
                scripts.append({"type":"inline", "content":sc.string or sc.get_text()})
    body = BeautifulSoup(str(soup.body) if soup.body else str(soup), "html.parser")
    for sc in body.find_all("script"):
        src = sc.get("src")
        if src:
            f = find_local(src, path)
            scripts.append({"type":"src", "src":public_url(f) if f else src})
        elif sc.string or sc.get_text(strip=True):
            scripts.append({"type":"inline", "content":sc.string or sc.get_text()})
        sc.decompose()
    for node in body.find_all(["head", "title", "meta", "link"]):
        node.decompose()
    return {"title":title, "html":rewrite_fragment(str(body), path, routes),
            "styles":styles, "scripts":scripts, "source":rel.as_posix()}

def main():
    if not SOURCE_DIR.is_dir():
        sys.exit(f"Folder sumber tidak ditemukan: {SOURCE_DIR}")
    if OUTPUT_DIR.exists():
        sys.exit(f"Folder output sudah ada: {OUTPUT_DIR}\nGanti OUTPUT_DIR atau pindahkan folder lama agar tidak tertimpa.")

    htmls = [p for p in SOURCE_DIR.rglob("*") if p.is_file()
             and p.suffix.lower() in (".html", ".htm")
             and not any(x in SKIP for x in p.parts)]
    htmls.sort()
    if not htmls:
        sys.exit("Tidak ada file HTML. Periksa SOURCE_DIR.")

    rels = [p.resolve().relative_to(SOURCE_DIR.resolve()) for p in htmls]
    routes = {r.as_posix():route_for(r) for r in rels}
    seen = set()
    for r in rels:
        key = r.as_posix()
        route = routes[key]
        if route in seen:
            route += "-" + hashlib.md5(key.encode()).hexdigest()[:6]
            routes[key] = route
        seen.add(route)

    (OUTPUT_DIR / "src/generated/pages").mkdir(parents=True)
    (OUTPUT_DIR / "src/components").mkdir(parents=True)
    (OUTPUT_DIR / "public/archive").mkdir(parents=True)

    copied = 0
    for p in SOURCE_DIR.rglob("*"):
        if not p.is_file() or p.suffix.lower() in (".html", ".htm"):
            continue
        if any(x in SKIP for x in p.parts):
            continue
        rel = p.resolve().relative_to(SOURCE_DIR.resolve())
        dest = OUTPUT_DIR / "public/archive" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(p, dest)
            copied += 1
        except OSError as err:
            print("[WARN]", p, err)

    pages, used = [], set()
    for i, (path, rel) in enumerate(zip(htmls, rels), 1):
        name = safe_name(rel.with_suffix("").as_posix().replace("/", "_"))
        if name in used:
            name += "_" + str(i)
        used.add(name)
        data = extract_page(path, rel, routes)
        data.update({"route":routes[rel.as_posix()], "component":name})
        folder = OUTPUT_DIR / "src/generated/pages"
        (folder / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        component = f'''import React from "react";
import PageRenderer from "../../components/PageRenderer";
import pageData from "./{name}.json";
export default function {name}() {{ return <PageRenderer page={{pageData}} />; }}
'''
        (folder / f"{name}.jsx").write_text(component, encoding="utf-8")
        pages.append({"route":data["route"], "component":name, "title":data["title"], "source":data["source"]})

    renderer = r'''import React, { useEffect } from "react";
export default function PageRenderer({ page }) {
  useEffect(() => {
    const marker = "archive-" + Math.random().toString(36).slice(2);
    const added = [];
    (page.styles || []).forEach((item) => {
      const el = document.createElement(item.type === "link" ? "link" : "style");
      if (item.type === "link") { el.rel = "stylesheet"; el.href = item.href; }
      else el.textContent = item.content || "";
      el.dataset.archivePage = marker; document.head.appendChild(el); added.push(el);
    });
    let cancelled = false;
    (async () => {
      for (const item of (page.scripts || [])) {
        if (cancelled) break;
        const el = document.createElement("script");
        el.dataset.archivePage = marker;
        if (item.type === "src") {
          el.src = item.src; el.async = false;
          await new Promise((resolve) => { el.onload = resolve; el.onerror = resolve; document.body.appendChild(el); });
        } else {
          el.textContent = item.content || ""; document.body.appendChild(el); added.push(el);
        }
      }
    })();
    return () => {
      cancelled = true;
      document.querySelectorAll(`[data-archive-page="${marker}"]`).forEach((el) => el.remove());
      added.forEach((el) => el.remove());
    };
  }, [page]);
  return <main className="archive-page"><div dangerouslySetInnerHTML={{ __html: page.html || "" }} /></main>;
}
'''
    (OUTPUT_DIR / "src/components/PageRenderer.jsx").write_text(renderer, encoding="utf-8")

    imports = [f'import {p["component"]} from "./generated/pages/{p["component"]}.jsx";' for p in pages]
    route_lines = [f'<Route key="{p["route"]}" path={{{json.dumps(p["route"])}}} element={{<{p["component"]} />}} />' for p in pages]
    app = '''import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
''' + "\n".join(imports) + '''
import "./style.css";
function NotFound() { return <div className="not-found"><h1>Halaman tidak ditemukan</h1><Link to="/">Kembali</Link></div>; }
export default function App() { return <BrowserRouter><Routes>
''' + "\n".join(route_lines) + '''
<Route path="*" element={<NotFound />} />
</Routes></BrowserRouter>; }
'''
    (OUTPUT_DIR / "src/App.jsx").write_text(app, encoding="utf-8")
    (OUTPUT_DIR / "src/main.jsx").write_text('''import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
''', encoding="utf-8")
    (OUTPUT_DIR / "src/style.css").write_text("html,body,#root{margin:0;min-height:100%;width:100%}body{overflow-x:hidden}.archive-page{width:100%;min-height:100vh}.archive-page img,.archive-page video{max-width:100%}.not-found{padding:40px;font-family:Arial,sans-serif}", encoding="utf-8")
    (OUTPUT_DIR / "index.html").write_text('''<!doctype html><html lang="id"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Attarivitation React</title></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>''', encoding="utf-8")
    package = {"name":"attarivitation-react-converted","private":True,"version":"1.0.0","type":"module",
      "scripts":{"dev":"vite --host 0.0.0.0 --port 3000","build":"vite build","preview":"vite preview --host 0.0.0.0"},
      "dependencies":{"@vitejs/plugin-react":"latest","vite":"latest","react":"latest","react-dom":"latest","react-router-dom":"latest"}}
    (OUTPUT_DIR / "package.json").write_text(json.dumps(package, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "vite.config.js").write_text('''import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()], server: { port: 3000, strictPort: true } });
''', encoding="utf-8")
    (OUTPUT_DIR / "ROUTE_MAP.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ("# Laporan Konversi Attarivitation\n\n"
      f"- Halaman HTML: {len(htmls)}\n- Aset disalin: {copied}\n- Komponen React pembungkus: {len(pages)}\n"
      "- Routing dibuat menggunakan React Router.\n\n"
      "## Catatan\nKonversi ini mempertahankan HTML asli di dalam komponen React, belum memecah semua HTML menjadi JSX modular. "
      "JavaScript lama mungkin gagal jika bergantung pada WordPress, plugin, urutan script, atau backend. "
      "Form RSVP, pembayaran, login, dan fitur backend harus dibangun ulang dan diuji.\n")
    (OUTPUT_DIR / "CONVERSION_REPORT.md").write_text(report, encoding="utf-8")
    print("KONVERSI SELESAI")
    print(f"HTML: {len(htmls)} | Aset: {copied} | Output: {OUTPUT_DIR}")
    print(f'cd "{OUTPUT_DIR}"')
    print("npm install")
    print("npm run dev")
    print("Buka http://localhost:3000")

if __name__ == "__main__":
    try:
        import bs4
    except ImportError:
        sys.exit("Jalankan: py -m pip install beautifulsoup4")
    main()
