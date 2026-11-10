
import os
import re
import json
import csv
import time
import hashlib
import mimetypes
from collections import deque
from urllib.parse import (
    urljoin, urlparse, unquote, urldefrag,
    parse_qsl, urlencode, urlunparse
)
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# =====================================================
# KONFIGURASI
# =====================================================

START_URL = "https://attarivitation.com/"
OUTPUT = "ATTARIVITATION_FULL_BACKUP"

MAX_PAGES = 3000
MAX_DEPTH = 0             # 0 = tanpa batas kedalaman
DELAY = 1
TIMEOUT = 40
RETRIES = 3
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB per file

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"

START_HOST = (urlparse(START_URL).hostname or "").lower()
ROOT_DOMAIN = START_HOST.removeprefix("www.")

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

visited = set()
downloaded = {}
failed = []
asset_queue = deque()
asset_queued = set()
robots_cache = {}

TOTAL_BYTES = 0

# =====================================================
# FOLDER
# =====================================================

FOLDERS = [
    "pages", "assets", "images", "css", "js",
    "fonts", "videos", "documents", "other"
]

os.makedirs(OUTPUT, exist_ok=True)

for folder in FOLDERS:
    os.makedirs(os.path.join(OUTPUT, folder), exist_ok=True)


# =====================================================
# URL UTILITIES
# =====================================================

def normalize_url(url):
    if not url:
        return None

    url = url.strip()

    if url.startswith(("javascript:", "mailto:", "tel:",
                       "data:", "blob:", "file:", "#")):
        return None

    url = urldefrag(url)[0]

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    # Remove tracking parameters
    ignored = {
        "utm_source", "utm_medium", "utm_campaign",
        "utm_term", "utm_content", "fbclid", "gclid"
    }

    query = [
        (k, v) for k, v in parse_qsl(
            parsed.query, keep_blank_values=True
        ) if k.lower() not in ignored
    ]

    parsed = parsed._replace(
        query=urlencode(query),
        fragment=""
    )

    return urlunparse(parsed)


def same_domain(url):
    try:
        host = (urlparse(url).hostname or "").lower()
        return (
            host == ROOT_DOMAIN or
            host == "www." + ROOT_DOMAIN
        )
    except Exception:
        return False


def safe_filename(value):
    value = re.sub(r'[<>:"/\\|?*]', "_", value)
    return value.strip(" .") or "index"


def get_extension(url, content_type=""):
    ext = os.path.splitext(urlparse(url).path)[1].lower()

    if ext and len(ext) <= 12:
        return ext

    content_type = content_type.split(";")[0].strip().lower()

    mapping = {
        "text/html": ".html",
        "text/css": ".css",
        "application/javascript": ".js",
        "text/javascript": ".js",
        "application/json": ".json",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
        "image/avif": ".avif",
        "image/x-icon": ".ico",
        "font/woff": ".woff",
        "font/woff2": ".woff2",
        "application/pdf": ".pdf",
        "video/mp4": ".mp4",
        "audio/mpeg": ".mp3",
    }

    return mapping.get(
        content_type,
        mimetypes.guess_extension(content_type) or ".bin"
    )


def category_for(url, content_type=""):
    ext = get_extension(url, content_type)

    if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp",
               ".avif", ".bmp", ".svg", ".ico", ".tif"]:
        return "images"

    if ext == ".css":
        return "css"

    if ext in [".js", ".mjs"]:
        return "js"

    if ext in [".woff", ".woff2", ".ttf", ".otf", ".eot"]:
        return "fonts"

    if ext in [".mp4", ".webm", ".mov", ".mp3", ".wav",
               ".ogg", ".m4a"]:
        return "videos"

    if ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx",
               ".zip", ".rar", ".7z", ".ppt", ".pptx"]:
        return "documents"

    return "other"


def local_file_path(url, category, content_type=""):
    parsed = urlparse(url)

    path = unquote(parsed.path).strip("/")

    if not path:
        path = "index"

    parts = [
        safe_filename(part)
        for part in path.split("/")
        if part not in ("", ".", "..")
    ]

    if not parts:
        parts = ["index"]

    filename = parts[-1]

    ext = get_extension(url, content_type)

    if not os.path.splitext(filename)[1]:
        filename += ext

    parts[-1] = filename

    # Keep external CDN assets separate
    if not same_domain(url):
        host = safe_filename(parsed.hostname or "external")
        parts.insert(0, host)

    base = os.path.join(OUTPUT, category)

    target = os.path.join(base, *parts)

    if parsed.query:
        name, ext = os.path.splitext(target)
        digest = hashlib.sha256(
            parsed.query.encode("utf-8")
        ).hexdigest()[:10]
        target = name + "_" + digest + ext

    target = os.path.abspath(target)

    if not target.startswith(os.path.abspath(base) + os.sep):
        raise ValueError("Unsafe file path")

    os.makedirs(os.path.dirname(target), exist_ok=True)

    return target


# =====================================================
# ROBOTS.TXT
# =====================================================

def check_robots(url):
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in robots_cache:
        parser = RobotFileParser()
        robots_url = origin + "/robots.txt"

        try:
            response = session.get(
                robots_url,
                timeout=15
            )

            if response.status_code == 200:
                parser.parse(response.text.splitlines())
                robots_cache[origin] = parser
                print("[ROBOTS] Berhasil:", robots_url)
            else:
                parser.allow_all = True
                robots_cache[origin] = parser
                print("[ROBOTS] Tidak tersedia, lanjut dengan allow all")

        except Exception as error:
            parser.allow_all = True
            robots_cache[origin] = parser
            print("[ROBOTS] Gagal dibaca:", error)

    return robots_cache[origin].can_fetch(USER_AGENT, url)


# =====================================================
# ASSET QUEUE
# =====================================================

def queue_asset(url):
    url = normalize_url(url)

    if not url:
        return

    parsed = urlparse(url)

    # Only HTTP(S), allow external assets discovered
    # from pages or CSS, but do not crawl external pages.
    if parsed.scheme not in ("http", "https"):
        return

    if url not in downloaded and url not in asset_queued:
        asset_queued.add(url)
        asset_queue.append(url)


# =====================================================
# DOWNLOAD ASSET
# =====================================================

def download_asset(url):
    global TOTAL_BYTES

    url = normalize_url(url)

    if not url or url in downloaded:
        return

    if not check_robots(url):
        return

    for attempt in range(RETRIES):
        try:
            response = session.get(
                url,
                timeout=TIMEOUT,
                stream=True,
                allow_redirects=True
            )

            response.raise_for_status()

            final_url = normalize_url(response.url) or url

            content_type = response.headers.get(
                "Content-Type", ""
            ).split(";")[0].lower()

            # Avoid downloading HTML pages as assets
            if "text/html" in content_type:
                return

            length = response.headers.get("Content-Length")

            if length and int(length) > MAX_FILE_SIZE:
                failed.append({
                    "url": url,
                    "error": "File exceeds size limit"
                })
                return

            category = category_for(url, content_type)

            path = local_file_path(
                url, category, content_type
            )

            sha = hashlib.sha256()
            size = 0

            with open(path, "wb") as file:
                for chunk in response.iter_content(1024 * 128):
                    if not chunk:
                        continue

                    size += len(chunk)

                    if size > MAX_FILE_SIZE:
                        raise ValueError("File exceeds size limit")

                    file.write(chunk)
                    sha.update(chunk)

            TOTAL_BYTES += size

            record = {
                "url": url,
                "final_url": final_url,
                "file": os.path.relpath(path, OUTPUT),
                "category": category,
                "content_type": content_type,
                "size_bytes": size,
                "sha256": sha.hexdigest()
            }

            downloaded[url] = record

            print(
                f"[FILE] {category}: {os.path.basename(path)} "
                f"({size / 1024:.1f} KB)"
            )

            # Find resources inside CSS
            if category == "css":
                try:
                    with open(
                        path, "r", encoding="utf-8",
                        errors="ignore"
                    ) as f:
                        css = f.read()

                    css_urls = re.findall(
                        r'url\(\s*["\']?(.*?)["\']?\s*\)',
                        css, re.I
                    )

                    imports = re.findall(
                        r'@import\s+(?:url\()?["\'](.*?)["\']',
                        css, re.I
                    )

                    for reference in css_urls + imports:
                        if reference.startswith(
                            ("data:", "blob:", "#")
                        ):
                            continue

                        queue_asset(urljoin(url, reference))

                except Exception as error:
                    print("[CSS ERROR]", error)

            return

        except Exception as error:
            if attempt == RETRIES - 1:
                failed.append({
                    "url": url,
                    "error": str(error)
                })
                print("[GAGAL]", url, error)
            else:
                time.sleep(2)


# =====================================================
# HTML EXTRACTION
# =====================================================

def extract_srcset(value, page_url):
    results = []

    if not value:
        return results

    for item in value.split(","):
        candidate = item.strip().split(" ")[0]

        if candidate:
            results.append(urljoin(page_url, candidate))

    return results


def extract_html_resources(html, page_url):
    soup = BeautifulSoup(html, "html.parser")

    links = set()
    assets = set()

    # Links to internal pages
    for tag in soup.find_all("a", href=True):
        target = normalize_url(
            urljoin(page_url, tag["href"])
        )

        if target and same_domain(target):
            links.add(target)

    # Images and picture sources
    for tag in soup.find_all(["img", "source"]):
        for attr in [
            "src", "data-src", "data-lazy-src",
            "data-original", "data-lazy",
            "data-original-src"
        ]:
            value = tag.get(attr)

            if value:
                assets.add(urljoin(page_url, value))

        assets.update(
            extract_srcset(tag.get("srcset"), page_url)
        )

        assets.update(
            extract_srcset(tag.get("data-srcset"), page_url)
        )

    # Scripts, stylesheets, icons, media, iframes
    for tag in soup.find_all(
        ["script", "link", "video", "audio", "iframe", "embed"]
    ):
        for attr in ["src", "href", "poster"]:
            value = tag.get(attr)

            if value:
                assets.add(urljoin(page_url, value))

    # Inline CSS
    for tag in soup.find_all(style=True):
        matches = re.findall(
            r'url\(\s*["\']?(.*?)["\']?\s*\)',
            tag["style"],
            re.I
        )

        for value in matches:
            if not value.startswith(("data:", "blob:", "#")):
                assets.add(urljoin(page_url, value))

    # Meta images
    for tag in soup.find_all("meta"):
        prop = (
            tag.get("property") or tag.get("name") or ""
        ).lower()

        if prop in [
            "og:image", "twitter:image",
            "og:video", "og:audio"
        ]:
            value = tag.get("content")

            if value:
                assets.add(urljoin(page_url, value))

    return links, assets


# =====================================================
# SAVE HTML
# =====================================================

def save_page(url, html):
    parsed = urlparse(url)

    path = unquote(parsed.path).strip("/")

    if not path:
        path = "index.html"
    elif path.endswith("/"):
        path += "index.html"
    elif not os.path.splitext(path)[1]:
        path += "/index.html"

    parts = [
        safe_filename(part)
        for part in path.split("/")
        if part not in ("", ".", "..")
    ]

    target = os.path.join(OUTPUT, "pages", *parts)

    if parsed.query:
        name, ext = os.path.splitext(target)
        digest = hashlib.sha256(
            parsed.query.encode()
        ).hexdigest()[:8]
        target = name + "_" + digest + ext

    target = os.path.abspath(target)

    base = os.path.abspath(os.path.join(OUTPUT, "pages"))

    if not target.startswith(base + os.sep):
        return

    os.makedirs(os.path.dirname(target), exist_ok=True)

    with open(target, "w", encoding="utf-8") as f:
        f.write(html)


# =====================================================
# PAGE CRAWLER
# =====================================================

def crawl_page(browser_page, url):
    print("\n" + "=" * 70)
    print("[HALAMAN]", url)

    try:
        response = browser_page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        if response and response.status >= 400:
            failed.append({
                "url": url,
                "error": f"HTTP {response.status}"
            })
            print("[HTTP ERROR]", response.status)
            return set()

        browser_page.wait_for_timeout(1500)

        # Scroll page to activate lazy loading
        try:
            browser_page.evaluate("""
                async () => {
                    const delay = ms =>
                        new Promise(resolve => setTimeout(resolve, ms));

                    for (
                        let y = 0;
                        y < document.body.scrollHeight;
                        y += 600
                    ) {
                        window.scrollTo(0, y);
                        await delay(200);
                    }

                    window.scrollTo(0, 0);
                }
            """)

            browser_page.wait_for_timeout(1000)

        except Exception:
            pass

        html = browser_page.content()

        save_page(url, html)

        links, assets = extract_html_resources(html, url)

        # Browser resource discovery
        try:
            resources = browser_page.evaluate("""
                () => performance.getEntriesByType("resource")
                    .map(item => item.name)
            """)

            for resource in resources:
                assets.add(resource)

        except Exception:
            pass

        for asset in assets:
            queue_asset(asset)

        print("[INFO] Internal links:", len(links))
        print("[INFO] Assets found:", len(assets))

        return links

    except Exception as error:
        failed.append({
            "url": url,
            "error": str(error)
        })

        print("[PAGE ERROR]", error)
        return set()


# =====================================================
# SAVE REPORTS
# =====================================================

def save_reports():
    manifest = {
        "website": START_URL,
        "backup_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_pages": len(visited),
        "total_files": len(downloaded),
        "failed_files": len(failed),
        "total_size_bytes": TOTAL_BYTES,
        "files": list(downloaded.values())
    }

    with open(
        os.path.join(OUTPUT, "manifest.json"),
        "w", encoding="utf-8"
    ) as f:
        json.dump(
            manifest, f,
            indent=2, ensure_ascii=False
        )

    with open(
        os.path.join(OUTPUT, "backup_report.csv"),
        "w", newline="", encoding="utf-8-sig"
    ) as f:

        fields = [
            "url", "final_url", "file", "category",
            "content_type", "size_bytes", "sha256"
        ]

        writer = csv.DictWriter(
            f, fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(downloaded.values())

    with open(
        os.path.join(OUTPUT, "failed_urls.json"),
        "w", encoding="utf-8"
    ) as f:
        json.dump(
            failed, f,
            indent=2, ensure_ascii=False
        )

    with open(
        os.path.join(OUTPUT, "visited_pages.txt"),
        "w", encoding="utf-8"
    ) as f:
        f.write("\n".join(sorted(visited)))


# =====================================================
# MAIN
# =====================================================

def main():
    print("=" * 70)
    print("       ATTARIVITATION FULL WEBSITE BACKUP")
    print("=" * 70)

    print("Website:", START_URL)
    print("Output:", os.path.abspath(OUTPUT))

    # Test connection before starting
    print("\n[TEST] Memeriksa koneksi website...")

    try:
        test = session.get(
            START_URL,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        test.raise_for_status()

        print("[OK] Website dapat diakses")
        print("[OK] HTTP:", test.status_code)
        print("[OK] URL:", test.url)
        print("[OK] HTML:", len(test.content), "bytes")

    except Exception as error:
        print("\n[ERROR] Website tidak dapat diakses:")
        print(error)
        print("Periksa koneksi internet atau URL.")
        return

    # Prepare queue
    page_queue = deque([(START_URL, 0)])

    print("\n[START] Memulai browser Chromium...")

    try:
        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(
                headless=True
            )

            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={
                    "width": 1440,
                    "height": 1000
                },
                ignore_https_errors=False
            )

            browser_page = context.new_page()

            while page_queue and len(visited) < MAX_PAGES:

                url, depth = page_queue.popleft()
                url = normalize_url(url)

                if not url or not same_domain(url):
                    continue

                if url in visited:
                    continue

                if not check_robots(url):
                    print("[ROBOTS BLOCK]", url)
                    continue

                visited.add(url)

                links = crawl_page(browser_page, url)

                if MAX_DEPTH == 0 or depth < MAX_DEPTH:
                    for link in links:
                        if (
                            link not in visited
                            and same_domain(link)
                        ):
                            page_queue.append(
                                (link, depth + 1)
                            )

                # Process assets in batches
                while asset_queue:
                    asset_url = asset_queue.popleft()
                    asset_queued.discard(asset_url)

                    if asset_url not in downloaded:
                        download_asset(asset_url)

                save_reports()

                print(
                    "\n[PROGRESS] Pages:",
                    len(visited),
                    "| Files:",
                    len(downloaded),
                    "| Failed:",
                    len(failed),
                    "| Remaining pages:",
                    len(page_queue)
                )

                time.sleep(DELAY)

            context.close()
            browser.close()

    except KeyboardInterrupt:
        print("\n[STOP] Backup dihentikan pengguna.")

    except Exception as error:
        print("\n[CRITICAL ERROR]", error)

    finally:
        # Save reports even if an error occurs
        save_reports()

        print("\n" + "=" * 70)
        print("             BACKUP SELESAI")
        print("=" * 70)

        print("Total halaman :", len(visited))
        print("Total file    :", len(downloaded))
        print("File gagal    :", len(failed))
        print(
            "Ukuran total  :",
            round(TOTAL_BYTES / 1024 / 1024, 2),
            "MB"
        )

        print("Lokasi        :", os.path.abspath(OUTPUT))
        print("=" * 70)


if __name__ == "__main__":
    main()
