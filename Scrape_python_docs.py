import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; PythonDocsScraper/1.0)"
}

MIN_CONTENT_LENGTH = 500
visited = set()


def clean_text(text):
    """Remove extra whitespace, blank lines, and navigation artifacts."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped in ('', '»', '«', '|', 'Next', 'Previous', 'index', 'modules'):
            continue
        if stripped.startswith('©') or 'Copyright' in stripped:
            continue
        cleaned.append(stripped)
    return '\n'.join(cleaned).strip()


def save_page(text, url, output_dir, prefix=""):
    """Save text and url to files with collision-safe naming."""
    path_part = url.split("docs.python.org/3/")[-1] if "docs.python.org" in url else url.split(".com/")[-1]
    file_name = path_part.replace("/", "_").replace(".html", "").strip("_")
    if prefix:
        file_name = f"{prefix}_{file_name}"

    txt_path = os.path.join(output_dir, f"{file_name}.txt")
    url_path = os.path.join(output_dir, f"{file_name}.url")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    with open(url_path, "w", encoding="utf-8") as f:
        f.write(url)

    print(f"  Saved: {file_name} ({len(text)} chars)")


# ============================================================
# 1. PYTHON OFFICIAL DOCS
# ============================================================

PYTHON_BASE = "https://docs.python.org/3/"
PYTHON_SECTIONS = ["tutorial/", "library/", "reference/", "faq/"]
PYTHON_OUT = "data/python_docs"

os.makedirs(PYTHON_OUT, exist_ok=True)


def get_python_links(section_url):
    """Get all .html links from a Python docs section index, with correct URL resolution."""
    resp = requests.get(section_url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".html") and not href.startswith("http"):
            full = urljoin(section_url, href)
            if full.startswith(PYTHON_BASE):
                links.append(full)
    return list(set(links))


def scrape_python_page(url):
    """Scrape a single Python docs page."""
    if url in visited:
        return
    visited.add(url)

    try:
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        content = soup.find("div", {"role": "main"})
        if not content:
            return

        text = clean_text(content.get_text())
        if len(text) < MIN_CONTENT_LENGTH:
            return

        save_page(text, url, PYTHON_OUT)
    except Exception as e:
        print(f"  Error scraping {url}: {e}")


print("=" * 50)
print("SCRAPING: Python Official Docs")
print("=" * 50)

for section in PYTHON_SECTIONS:
    section_url = PYTHON_BASE + section
    print(f"\nSection: {section_url}")
    links = get_python_links(section_url)
    print(f"  Found {len(links)} pages")

    for link in sorted(links):
        scrape_python_page(link)
        time.sleep(0.5)


# ============================================================
# 2. REALPYTHON
# ============================================================

REALPYTHON_OUT = "data/realpython"
os.makedirs(REALPYTHON_OUT, exist_ok=True)

REALPYTHON_URLS = [
    # Core Python
    "https://realpython.com/python-data-types/",
    "https://realpython.com/python-variables/",
    "https://realpython.com/python-strings/",
    "https://realpython.com/python-lists-tuples/",
    "https://realpython.com/python-dicts/",
    "https://realpython.com/python-sets/",
    "https://realpython.com/python-conditional-statements/",
    "https://realpython.com/python-for-loop/",
    "https://realpython.com/python-while-loop/",
    "https://realpython.com/python-functions/",
    "https://realpython.com/python-lambda/",
    "https://realpython.com/python-scope-legb-rule/",
    "https://realpython.com/python-return-statement/",
    # OOP
    "https://realpython.com/python3-object-oriented-programming/",
    "https://realpython.com/python-classes/",
    "https://realpython.com/inheritance-composition-python/",
    "https://realpython.com/python-super/",
    "https://realpython.com/python-metaclasses/",
    "https://realpython.com/python-descriptors/",
    # Advanced
    "https://realpython.com/python-decorators/",
    "https://realpython.com/primer-on-python-decorators/",
    "https://realpython.com/python-generators/",
    "https://realpython.com/introduction-to-python-generators/",
    "https://realpython.com/python-iterators-iterables/",
    "https://realpython.com/python-context-managers/",
    "https://realpython.com/python-with-statement/",
    "https://realpython.com/async-io-python/",
    "https://realpython.com/python-concurrency/",
    "https://realpython.com/python-gil/",
    "https://realpython.com/python-type-checking/",
    "https://realpython.com/python-walrus-operator/",
    "https://realpython.com/python-match-case/",
    "https://realpython.com/python-enum/",
    "https://realpython.com/python-data-classes/",
    # Error handling & debugging
    "https://realpython.com/python-exceptions/",
    "https://realpython.com/python-traceback/",
    "https://realpython.com/python-logging/",
    "https://realpython.com/python-debugging-pdb/",
    # File I/O & data
    "https://realpython.com/read-write-files-python/",
    "https://realpython.com/working-with-files-in-python/",
    "https://realpython.com/python-csv/",
    "https://realpython.com/python-json/",
    "https://realpython.com/python-pathlib/",
    # Testing
    "https://realpython.com/python-testing/",
    "https://realpython.com/pytest-python-testing/",
    # Modules & packaging
    "https://realpython.com/python-modules-packages/",
    "https://realpython.com/python-import/",
    "https://realpython.com/python-virtual-environments-a-primer/",
    "https://realpython.com/python-pip/",
    # Common libraries
    "https://realpython.com/python-requests/",
    "https://realpython.com/python-collections-module/",
    "https://realpython.com/python-itertools/",
    "https://realpython.com/python-map-function/",
    "https://realpython.com/python-filter-function/",
    "https://realpython.com/python-reduce-function/",
    "https://realpython.com/python-zip-function/",
    "https://realpython.com/python-string-formatting/",
    "https://realpython.com/python-f-strings/",
    "https://realpython.com/regex-python/",
]


def scrape_realpython(url):
    """Scrape a single RealPython article."""
    if url in visited:
        return
    visited.add(url)

    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"  Skipped (HTTP {resp.status_code}): {url}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        # RealPython article content is in <div class="article-body">
        content = soup.find("div", class_="article-body")
        if not content:
            content = soup.find("article")
        if not content:
            content = soup.find("div", class_="content")
        if not content:
            print(f"  Skipped (no content found): {url}")
            return

        # Remove sidebar, nav, ads, related articles
        for tag in content.find_all(["nav", "aside", "footer", "script", "style"]):
            tag.decompose()
        for div in content.find_all("div", class_=re.compile(r"sidebar|promo|newsletter|related|ad")):
            div.decompose()

        text = clean_text(content.get_text())
        if len(text) < MIN_CONTENT_LENGTH:
            print(f"  Skipped (too short): {url}")
            return

        save_page(text, url, REALPYTHON_OUT, prefix="rp")
    except Exception as e:
        print(f"  Error scraping {url}: {e}")


print("\n" + "=" * 50)
print("SCRAPING: RealPython Articles")
print("=" * 50)
print(f"  Target: {len(REALPYTHON_URLS)} articles\n")

for url in REALPYTHON_URLS:
    scrape_realpython(url)
    time.sleep(1.0)  # be respectful to RealPython


print("\n" + "=" * 50)
print("SCRAPING COMPLETE")
print(f"  Total pages scraped: {len(visited)}")
print("=" * 50)
