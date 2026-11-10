import os
import re
import json
import csv
import shutil
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURATION
# ==========================================

BASE = Path(__file__).resolve().parent
OUTPUT = BASE.parent / "ATTARIVITATION_AUDIT"

EXCLUDE = {
    "venv", "node_modules", ".git",
    "__pycache__", "ATTARIVITATION_AUDIT"
}

ASSET_EXTENSIONS = {
    ".css": "css",
    ".js": "js",
    ".jpg": "images",
    ".jpeg": "images",
    ".png": "images",
    ".webp": "images",
    ".gif": "images",
    ".svg": "icons",
    ".ico": "icons",
    ".woff": "fonts",
    ".woff2": "fonts",
    ".ttf": "fonts",
    ".otf": "fonts",
    ".mp3": "audio",
    ".wav": "audio",
    ".ogg": "audio",
    ".mp4": "video",
    ".webm": "video",
    ".json": "data"
}

OUTPUT.mkdir(exist_ok=True)

# ==========================================
# UTILITIES
# ==========================================

def relative_path(path):
    return path.relative_to(BASE).as_posix()


def get_category(url, title, text):
    value = (url + " " + title + " " + text[:1500]).lower()

    rules = [
        ("Homepage", ["home", "beranda"]),
        ("Undangan", ["undangan", "invitation", "wedding-invitation"]),
        ("Template", ["template", "themes", "tema-undangan"]),
        ("Pricing", ["harga", "pricing", "paket"]),
        ("Blog", ["blog", "artikel", "category", "tag"]),
        ("Contact", ["contact", "kontak", "hubungi"]),
        ("About", ["about", "tentang-kami"]),
        ("Login", ["login", "signin", "register", "daftar"]),
        ("Product", ["product", "produk", "layanan"]),
        ("Form", ["form", "booking", "pesan"])
    ]

    for category, keywords in rules:
        if any(word in value for word in keywords):
            return category

    if url in ["/", "/index", "/index.html"]:
        return "Homepage"

    return "Other"


def save_json(name, data):
    with open(OUTPUT / name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==========================================
# FIND HTML FILES
# ==========================================

print("\n[1/7] Memindai halaman HTML...")

html_files = []

for file in BASE.rglob("*"):
    if not file.is_file():
        continue

    if any(part in EXCLUDE for part in file.relative_to(BASE).parts):
        continue

    if file.suffix.lower() in [".html", ".htm"]:
        html_files.append(file)

print("Total halaman:", len(html_files))

# ==========================================
# PAGE AUDIT
# ==========================================

print("\n[2/7] Audit halaman...")

pages = []
category_count = Counter()
asset_usage = defaultdict(set)
template_signatures = defaultdict(list)
all_links = []

for index, file in enumerate(html_files, 1):

    try:
        html = file.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title else file.stem
        )

        text = soup.get_text(" ", strip=True)

        path = relative_path(file)

        category = get_category(path, title, text)

        css = [
            x.get("href")
            for x in soup.find_all("link", href=True)
            if "stylesheet" in " ".join(x.get("rel", []))
        ]

        js = [
            x.get("src")
            for x in soup.find_all("script", src=True)
        ]

        images = [
            x.get("src") or x.get("data-src")
            for x in soup.find_all("img")
            if x.get("src") or x.get("data-src")
        ]

        audio = [
            x.get("src")
            for x in soup.find_all("audio", src=True)
        ]

        videos = [
            x.get("src")
            for x in soup.find_all("video", src=True)
        ]

        links = [
            x.get("href")
            for x in soup.find_all("a", href=True)
        ]

        features = []

        feature_rules = {
            "Countdown": ["countdown", "timer"],
            "RSVP": ["rsvp"],
            "Gallery": ["gallery", "swiper", "lightbox"],
            "Music": ["audio", "music", "sound"],
            "Guest Name": ["guest", "to="],
            "Maps": ["google.com/maps", "maps/embed"],
            "Love Story": ["love-story", "story"],
            "Gift": ["gift", "rekening", "bank"],
            "Animation": ["animation", "aos", "wow"],
            "Form": ["form", "input", "textarea"]
        }

        lower_html = html.lower()

        for feature, keywords in feature_rules.items():
            if any(keyword in lower_html for keyword in keywords):
                features.append(feature)

        # Identifikasi kandidat template
        headings = [
            x.get_text(" ", strip=True)
            for x in soup.find_all(["h1", "h2"])
        ]

        sections = [
            x.get("id") or x.get("class")
            for x in soup.find_all("section")
        ]

        signature_source = json.dumps({
            "headings": headings[:8],
            "sections": sections[:15]
        }, ensure_ascii=False)

        signature = hashlib.md5(
            signature_source.encode("utf-8")
        ).hexdigest()

        if category in ["Template", "Undangan"]:
            template_signatures[signature].append(path)

        page = {
            "id": index,
            "file": path,
            "url": "/" + path,
            "title": title,
            "category": category,
            "css": css,
            "javascript": js,
            "images": images,
            "audio": audio,
            "videos": videos,
            "links": links,
            "headings": headings,
            "sections": sections,
            "features": features,
            "template_signature": signature
        }

        pages.append(page)
        category_count[category] += 1

        for asset in css + js + images + audio + videos:
            asset_usage[asset].add(path)

        for link in links:
            all_links.append({
                "source": path,
                "target": link
            })

        if index % 25 == 0:
            print(f"  Diproses {index}/{len(html_files)}")

    except Exception as error:
        print("Gagal:", file, error)

save_json("pages.json", pages)

# ==========================================
# ASSET INVENTORY
# ==========================================

print("\n[3/7] Inventarisasi aset...")

assets = []

for file in BASE.rglob("*"):

    if not file.is_file():
        continue

    if any(part in EXCLUDE for part in file.relative_to(BASE).parts):
        continue

    extension = file.suffix.lower()

    if extension not in ASSET_EXTENSIONS:
        continue

    assets.append({
        "file": relative_path(file),
        "type": ASSET_EXTENSIONS[extension],
        "extension": extension,
        "size_bytes": file.stat().st_size,
        "used_by": sorted(asset_usage.get(relative_path(file), []))
    })

save_json("assets.json", assets)

# ==========================================
# TEMPLATE GROUPING
# ==========================================

print("\n[4/7] Mengelompokkan template...")

templates = []

for signature, files in template_signatures.items():

    templates.append({
        "signature": signature,
        "variation_count": len(files),
        "files": files
    })

templates.sort(
    key=lambda item: item["variation_count"],
    reverse=True
)

save_json("templates.json", templates)

# ==========================================
# FEATURE AUDIT
# ==========================================

print("\n[5/7] Audit fitur...")

feature_count = Counter()

for page in pages:
    for feature in page["features"]:
        feature_count[feature] += 1

feature_report = [
    {
        "feature": feature,
        "page_count": count
    }
    for feature, count in feature_count.most_common()
]

save_json("features.json", feature_report)

# ==========================================
# ROUTE AND LINK AUDIT
# ==========================================

print("\n[6/7] Audit navigasi...")

save_json("links.json", all_links)

# ==========================================
# MARKDOWN REPORTS
# ==========================================

print("\n[7/7] Membuat dokumentasi...")

def write_report(filename, title, rows):

    with open(OUTPUT / filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")

        for row in rows:
            f.write(row + "\n")

# PAGE AUDIT

lines = [
    f"Total halaman: {len(pages)}",
    "",
    "## Ringkasan kategori",
    ""
]

for category, count in category_count.most_common():
    lines.append(f"- {category}: {count}")

lines += ["", "## Detail halaman", ""]

for page in pages:
    lines.append(f"### {page['title']}")
    lines.append(f"- File: `{page['file']}`")
    lines.append(f"- Kategori: {page['category']}")
    lines.append(f"- CSS: {len(page['css'])}")
    lines.append(f"- JavaScript: {len(page['javascript'])}")
    lines.append(f"- Gambar: {len(page['images'])}")
    lines.append(f"- Fitur: {', '.join(page['features'])}")
    lines.append("")

write_report("PAGE_AUDIT.md", "PAGE AUDIT", lines)

# TEMPLATE AUDIT

lines = [
    f"Total kelompok struktur template: {len(templates)}",
    ""
]

for index, template in enumerate(templates, 1):
    lines.append(f"## Kelompok {index}")
    lines.append(f"- Variasi: {template['variation_count']}")
    for file in template["files"]:
        lines.append(f"- `{file}`")
    lines.append("")

write_report("TEMPLATE_AUDIT.md", "TEMPLATE AUDIT", lines)

# ASSET AUDIT

asset_count = Counter(x["type"] for x in assets)

lines = [f"Total aset: {len(assets)}", ""]

for kind, count in asset_count.items():
    lines.append(f"- {kind}: {count}")

lines += ["", "## Daftar aset", ""]

for asset in assets:
    lines.append(
        f"- `{asset['file']}` — {asset['type']} — "
        f"{asset['size_bytes']} bytes"
    )

write_report("ASSET_AUDIT.md", "ASSET AUDIT", lines)

# FEATURE AUDIT

lines = ["## Fitur yang teridentifikasi", ""]

for item in feature_report:
    lines.append(
        f"- {item['feature']}: ditemukan pada "
        f"{item['page_count']} halaman"
    )

write_report("FEATURE_AUDIT.md", "FEATURE AUDIT", lines)

# ROUTE MAPPING

lines = ["## Route mapping", ""]

for page in pages:
    lines.append(
        f"- `{page['url']}` -> `{page['file']}`"
    )

write_report("ROUTE_MAPPING.md", "ROUTE MAPPING", lines)

# CSV

with open(
    OUTPUT / "pages.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "id", "file", "url", "title",
            "category", "features"
        ]
    )

    writer.writeheader()

    for page in pages:
        writer.writerow({
            **{
                key: page[key]
                for key in [
                    "id", "file", "url",
                    "title", "category"
                ]
            },
            "features": ", ".join(page["features"])
        })

# SUMMARY

summary = {
    "total_pages": len(pages),
    "categories": dict(category_count),
    "total_assets": len(assets),
    "asset_types": dict(asset_count),
    "template_groups": len(templates),
    "features": feature_report
}

save_json("SUMMARY.json", summary)

print("\n======================================")
print("AUDIT ATTARIVITATION SELESAI")
print("======================================")
print("Halaman       :", len(pages))
print("Aset          :", len(assets))
print("Template group:", len(templates))
print("Kategori      :", dict(category_count))
print("Output        :", OUTPUT)
print("======================================")