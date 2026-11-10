import re
import json
import shutil
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urlparse, unquote

# =========================================================
# KONFIGURASI
# =========================================================

SOURCE_DIR = Path(r"D:\ATTARIVITATION_BACKUP")
OUTPUT_DIR = Path(r"D:\ATTARIVITATION_REACT_V3")

ASSET_DIR = OUTPUT_DIR / "public" / "archive"
PAGES_DIR = OUTPUT_DIR / "src" / "pages"

IGNORE_DIRS = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build"
}

SKIP_TAGS = {
    "script",
    "style",
    "meta",
    "link",
    "title",
    "base",
    "noscript"
}

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr",
    "img", "input", "link", "meta", "param",
    "source", "track", "wbr"
}

ATTRIBUTE_MAP = {
    "class": "className",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "readonly": "readOnly",
    "maxlength": "maxLength",
    "colspan": "colSpan",
    "rowspan": "rowSpan",
    "contenteditable": "contentEditable",
    "crossorigin": "crossOrigin",
    "autocomplete": "autoComplete",
    "autofocus": "autoFocus",
    "srcset": "srcSet",
    "usemap": "useMap",
    "frameborder": "frameBorder",
    "cellpadding": "cellPadding",
    "cellspacing": "cellSpacing",
    "datetime": "dateTime",
    "formaction": "formAction",
    "formenctype": "formEncType",
    "formmethod": "formMethod",
    "formtarget": "formTarget",
    "novalidate": "noValidate",
    "playsinline": "playsInline",
    "allowfullscreen": "allowFullScreen",
}

BOOLEAN_ATTRIBUTES = {
    "disabled", "checked", "selected", "multiple",
    "required", "readonly", "autofocus", "autoplay",
    "controls", "loop", "muted", "hidden",
    "novalidate", "open", "playsinline",
    "allowfullscreen", "reversed", "defer",
    "async", "ismap", "itemscope"
}

URL_ATTRIBUTES = {
    "src", "href", "poster", "data-src",
    "data-lazy-src", "data-original"
}

WARNINGS = []
ROUTES = []


# =========================================================
# UTILITAS
# =========================================================

def safe_name(value):
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value)
    return value.strip("-_").lower() or "page"


def escape_jsx_text(value):
    value = value.replace("{", "&#123;")
    value = value.replace("}", "&#125;")
    return value


def js_string(value):
    return json.dumps(str(value), ensure_ascii=False)


def to_camel_case(value):
    parts = value.split("-")
    return parts[0] + "".join(x.capitalize() for x in parts[1:])


def convert_style(style_string):
    result = {}

    for declaration in style_string.split(";"):
        if ":" not in declaration:
            continue

        key, value = declaration.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not key or not value:
            continue

        if key.startswith("--"):
            result[key] = value
        else:
            result[to_camel_case(key)] = value

    return result


def find_asset(source_file, url):
    if not url or url.startswith((
        "http://", "https://", "//", "data:",
        "blob:", "mailto:", "tel:", "#", "javascript:"
    )):
        return url

    parsed = urlparse(url)

    if parsed.scheme or parsed.netloc:
        return url

    relative = unquote(parsed.path).replace("\\", "/").lstrip("/")

    candidates = [
        source_file.parent / relative,
        SOURCE_DIR / relative,
    ]

    for candidate in candidates:
        if candidate.is_file():
            try:
                relative_path = candidate.relative_to(SOURCE_DIR)
                return "/archive/" + relative_path.as_posix()
            except ValueError:
                pass

    return url


# =========================================================
# KONVERSI ATRIBUT HTML KE JSX
# =========================================================

def convert_attributes(tag, source_file):
    attributes = []

    for original_name, value in tag.attrs.items():

        name = original_name.lower()

        # Event handler HTML tidak bisa diterjemahkan otomatis
        # menjadi fungsi React.
        if name.startswith("on"):
            WARNINGS.append({
                "file": str(source_file),
                "type": "INLINE_EVENT",
                "attribute": name,
                "message": "Event handler perlu diubah manual menjadi React event."
            })
            continue

        jsx_name = ATTRIBUTE_MAP.get(name, original_name)

        if isinstance(value, list):
            value = " ".join(str(item) for item in value)

        if name == "style":
            style_object = convert_style(str(value))
            attributes.append(
                f"style={{{json.dumps(style_object, ensure_ascii=False)}}}"
            )
            continue

        if name in URL_ATTRIBUTES:
            value = find_asset(source_file, str(value))

        elif name == "srcset":
            entries = []

            for entry in str(value).split(","):
                parts = entry.strip().split()

                if not parts:
                    continue

                parts[0] = find_asset(source_file, parts[0])
                entries.append(" ".join(parts))

            value = ", ".join(entries)

        if name in BOOLEAN_ATTRIBUTES:
            if value is not None:
                attributes.append(f"{jsx_name}={{true}}")
            continue

        if value is None:
            continue

        attributes.append(f"{jsx_name}={{{js_string(value)}}}")

    return " ".join(attributes)


# =========================================================
# KONVERSI DOM MENJADI JSX
# =========================================================

def convert_node(node, source_file, depth=0):
    indent = "  " * depth

    if isinstance(node, NavigableString):
        text = str(node)

        if not text.strip():
            return ""

        return indent + escape_jsx_text(text.strip())

    if not isinstance(node, Tag):
        return ""

    tag_name = node.name.lower()

    if tag_name in SKIP_TAGS:
        return ""

    attributes = convert_attributes(node, source_file)

    opening = (
        f"<{tag_name} {attributes}>"
        if attributes
        else f"<{tag_name}>"
    )

    if tag_name in VOID_TAGS:
        return (
            f"<{tag_name} {attributes} />"
            if attributes
            else f"<{tag_name} />"
        )

    children = []

    for child in node.children:
        converted = convert_node(
            child,
            source_file,
            depth + 1
        )

        if converted:
            children.append(converted)

    if not children:
        return f"<{tag_name} {attributes} />" if attributes else f"<{tag_name} />"

    children_text = "\n".join(children)

    return (
        f"{indent}{opening}\n"
        f"{children_text}\n"
        f"{indent}</{tag_name}>"
    )


# =========================================================
# EKSTRAK CSS DAN JAVASCRIPT
# =========================================================

def extract_dependencies(soup, source_file):
    stylesheets = []
    scripts = []

    for link in soup.find_all("link", href=True):
        rel = link.get("rel", [])

        if isinstance(rel, str):
            rel = rel.split()

        if "stylesheet" in rel:
            stylesheets.append(
                find_asset(source_file, link["href"])
            )

    for script in soup.find_all("script", src=True):
        scripts.append(
            find_asset(source_file, script["src"])
        )

    return stylesheets, scripts


# =========================================================
# GENERATE KOMPONEN REACT
# =========================================================

def generate_component(html_file):
    relative = html_file.relative_to(SOURCE_DIR)

    slug = safe_name(
        str(relative.with_suffix(""))
        .replace("\\", "-")
        .replace("/", "-")
    )

    component_name = "".join(
        part.capitalize()
        for part in slug.split("-")
    ) or "GeneratedPage"

    with open(html_file, "r", encoding="utf-8", errors="replace") as file:
        html = file.read()

    soup = BeautifulSoup(html, "html.parser")

    stylesheets, scripts = extract_dependencies(
        soup,
        html_file
    )

    body = soup.body or soup

    jsx_parts = []

    for child in body.children:
        converted = convert_node(child, html_file)

        if converted:
            jsx_parts.append(converted)

    jsx_content = "\n".join(jsx_parts)

    # Tambahkan stylesheet dan script secara runtime.
    dependency_code = ""

    if stylesheets or scripts:
        dependency_code = """
  React.useEffect(() => {
    const elements = [];

    const addStylesheet = (href) => {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
      elements.push(link);
    };

    const addScript = (src) => {
      const script = document.createElement("script");
      script.src = src;
      script.async = false;
      document.body.appendChild(script);
      elements.push(script);
    };

"""

        for stylesheet in stylesheets:
            dependency_code += (
                f"    addStylesheet({js_string(stylesheet)});\n"
            )

        for script in scripts:
            dependency_code += (
                f"    addScript({js_string(script)});\n"
            )

        dependency_code += """
    return () => {
      elements.forEach(element => element.remove());
    };
  }, []);
"""

    component = f"""import React from "react";

export default function {component_name}() {{
{dependency_code}
  return (
    <>
{jsx_content}
    </>
  );
}}
"""

    output_file = PAGES_DIR / f"{slug}.jsx"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(
        component,
        encoding="utf-8"
    )

    route_path = "/" + slug

    ROUTES.append({
        "path": route_path,
        "component": component_name,
        "file": f"./pages/{slug}.jsx",
        "source": str(relative)
    })

    return output_file


# =========================================================
# COPY ASSET
# =========================================================

def copy_assets():
    count = 0

    for file in SOURCE_DIR.rglob("*"):

        if not file.is_file():
            continue

        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        if file.suffix.lower() in {".html", ".htm"}:
            continue

        try:
            relative = file.relative_to(SOURCE_DIR)
            destination = ASSET_DIR / relative

            destination.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            shutil.copy2(file, destination)
            count += 1

        except Exception as error:
            WARNINGS.append({
                "file": str(file),
                "type": "ASSET_COPY_ERROR",
                "message": str(error)
            })

    return count


# =========================================================
# GENERATE APP ROUTER
# =========================================================

def generate_app():
    imports = []
    routes = []

    for index, route in enumerate(ROUTES):
        imports.append(
            f'import Page{index} from "{route["file"]}";'
        )

        routes.append(
            f'<Route path="{route["path"]}" element={{<Page{index} />}} />'
        )

    content = f"""import React from "react";
import {{ BrowserRouter, Routes, Route }} from "react-router-dom";

{chr(10).join(imports)}

export default function App() {{
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={{<Page0 />}} />
        {chr(10).join(routes)}
        <Route path="*" element={{<div>Halaman tidak ditemukan</div>}} />
      </Routes>
    </BrowserRouter>
  );
}}
"""

    (OUTPUT_DIR / "src" / "App.jsx").write_text(
        content,
        encoding="utf-8"
    )


# =========================================================
# GENERATE PROJECT REACT
# =========================================================

def generate_project_files():
    package = {
        "name": "attarivitation-react",
        "version": "1.0.0",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "vite --host 0.0.0.0",
            "build": "vite build",
            "preview": "vite preview"
        },
        "dependencies": {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
            "react-router-dom": "^6.28.0"
        },
        "devDependencies": {
            "vite": "^5.4.0"
        }
    }

    (OUTPUT_DIR / "package.json").write_text(
        json.dumps(package, indent=2),
        encoding="utf-8"
    )

    (OUTPUT_DIR / "index.html").write_text(
        """<!doctype html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Attarivitation</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
""",
        encoding="utf-8"
    )

    (OUTPUT_DIR / "src" / "main.jsx").write_text(
        """import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",
        encoding="utf-8"
    )


# =========================================================
# MAIN
# =========================================================

def main():
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Folder sumber tidak ditemukan: {SOURCE_DIR}"
        )

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Folder output sudah ada: {OUTPUT_DIR}\n"
            "Ganti OUTPUT_DIR atau pindahkan folder lama terlebih dahulu."
        )

    print("Membuat struktur React...")

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    html_files = []

    for file in SOURCE_DIR.rglob("*"):
        if file.is_file() and file.suffix.lower() in {".html", ".htm"}:
            if not any(part in IGNORE_DIRS for part in file.parts):
                html_files.append(file)

    html_files.sort()

    if not html_files:
        raise RuntimeError("Tidak ditemukan file HTML.")

    print(f"Ditemukan {len(html_files)} halaman HTML.")

    successful = 0

    for index, html_file in enumerate(html_files, start=1):
        try:
            generate_component(html_file)
            successful += 1

            print(
                f"[{index}/{len(html_files)}] "
                f"{html_file.name}"
            )

        except Exception as error:
            WARNINGS.append({
                "file": str(html_file),
                "type": "HTML_CONVERSION_ERROR",
                "message": str(error)
            })

    print("Menyalin aset...")
    asset_count = copy_assets()

    generate_app()
    generate_project_files()

    (OUTPUT_DIR / "ROUTE_MAP.json").write_text(
        json.dumps(ROUTES, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    (OUTPUT_DIR / "CONVERSION_WARNINGS.json").write_text(
        json.dumps(WARNINGS, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    report = f"""
# ATTARIVITATION HTML TO REACT

- Total HTML: {len(html_files)}
- Berhasil dikonversi: {successful}
- Gagal: {len(html_files) - successful}
- Aset disalin: {asset_count}
- Jumlah route: {len(ROUTES)}
- Jumlah peringatan: {len(WARNINGS)}

## Catatan

Konversi ini menghasilkan JSX dari struktur DOM HTML.
JavaScript lama, event handler, dan fitur backend belum otomatis
menjadi logika React. Periksa CONVERSION_WARNINGS.json.
"""

    (OUTPUT_DIR / "CONVERSION_REPORT.md").write_text(
        report,
        encoding="utf-8"
    )

    print("\n====================================")
    print("KONVERSI SELESAI")
    print("====================================")
    print(f"Halaman HTML : {len(html_files)}")
    print(f"Berhasil     : {successful}")
    print(f"Aset         : {asset_count}")
    print(f"Peringatan   : {len(WARNINGS)}")
    print(f"Output       : {OUTPUT_DIR}")
    print("\nJalankan:")
    print(f'cd "{OUTPUT_DIR}"')
    print("npm install")
    print("npm run dev")


if __name__ == "__main__":
    main()