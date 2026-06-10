#!/usr/bin/env python3
"""Download Sportmonks Football API v3 docs into a single local Markdown file."""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

INDEX_URL = "https://docs.sportmonks.com/llms.txt"
FOOTBALL_SECTION = "Football API 3.0"
EXCLUDED_PATH_SEGMENTS = (
    "/motorsport-api/",
    "/odds-api/",
    "/core-api/",
    "/football-widgets/",
    "/beta-documentation/",
)

REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 0.4
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0
USER_AGENT = "ModelloPrevisionaleCalcistico/1.0 (docs-fetcher)"

URL_PATTERN = re.compile(r"https://docs\.sportmonks\.com/v3/[^\s\)]+\.md")
LINK_WITH_TITLE_PATTERN = re.compile(
    r"\[([^\]]*)\]\((https://docs\.sportmonks\.com/v3/[^\)]+?\.md)\)"
)
LINK_PATTERN = re.compile(r"\[[^\]]*\]\((https://docs\.sportmonks\.com/v3/[^\)]+?\.md)\)")

PAGE_SEPARATOR = (
    "\n\n---\n\n"
    "<!-- Page separator -->\n\n"
    "---\n\n"
)


class HttpClient:
    """Minimal HTTP client using urllib (reliable SSL on Windows Store Python)."""

    def __init__(self, user_agent: str = USER_AGENT) -> None:
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/markdown,text/plain,*/*",
        }

    def get_text(self, url: str) -> str:
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                request = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                    raw = response.read()
                    charset = response.headers.get_content_charset() or "utf-8"
                    return raw.decode(charset, errors="replace")
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        raise RuntimeError(f"Failed to fetch {url}") from last_error


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def is_football_v3_url(url: str) -> bool:
    if "/v3/" not in url or not url.endswith(".md"):
        return False
    return not any(segment in url for segment in EXCLUDED_PATH_SEGMENTS)


def _iter_football_section_lines(index_text: str):
    in_football_section = False
    for line in index_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            in_football_section = title == FOOTBALL_SECTION
            continue
        if in_football_section:
            yield line


def extract_urls_from_section(index_text: str) -> list[str]:
    """Extract unique Football API v3 markdown URLs preserving index order."""
    seen: set[str] = set()
    urls: list[str] = []

    for line in _iter_football_section_lines(index_text):
        for match in LINK_PATTERN.finditer(line):
            url = match.group(1)
            if is_football_v3_url(url) and url not in seen:
                seen.add(url)
                urls.append(url)

        for url in URL_PATTERN.findall(line):
            if is_football_v3_url(url) and url not in seen:
                seen.add(url)
                urls.append(url)

    return urls


def extract_url_titles_from_section(index_text: str) -> dict[str, str]:
    """Map Football API v3 URLs to their link titles from llms.txt."""
    titles: dict[str, str] = {}
    for line in _iter_football_section_lines(index_text):
        for match in LINK_WITH_TITLE_PATTERN.finditer(line):
            title, url = match.group(1).strip(), match.group(2)
            if is_football_v3_url(url) and title:
                titles[url] = title
    return titles


def url_category(url: str) -> str:
    """Derive a human-readable category from the docs URL path."""
    marker = "/v3/"
    if marker not in url:
        return "other"
    path = url.split(marker, 1)[1].removesuffix(".md")
    parts = path.split("/")
    if not parts:
        return "other"
    if parts[0] in {"welcome", "changelog", "api", "api-quick-nav", "api-coach"}:
        return parts[0]
    if parts[0] == "sportmonks-ai-docs":
        return "ai-docs/" + (parts[1] if len(parts) > 1 else "root")
    if parts[0] == "endpoints-and-entities":
        if len(parts) >= 3 and parts[1] == "endpoints":
            return f"endpoints/{parts[2]}"
        if len(parts) >= 2:
            return f"entities/{parts[1]}"
    if parts[0] == "tutorials-and-guides":
        return "tutorials-and-guides/" + (parts[1] if len(parts) > 1 else "root")
    return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]


def write_pages_catalog(
    docs_dir: Path,
    urls: list[str],
    index_text: str,
    failures: list[tuple[str, str]] | None = None,
) -> Path:
    """Write a categorized catalog of every Football API v3 page in the bundle."""
    catalog_path = docs_dir / "sportmonks-football-v3-pagine.md"
    titles = extract_url_titles_from_section(index_text)
    failed_urls = {url for url, _ in (failures or [])}
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    by_category: dict[str, list[tuple[int, str, str, str]]] = {}
    for index, url in enumerate(urls, start=1):
        title = titles.get(url, url.rsplit("/", 1)[-1].removesuffix(".md"))
        status = "failed" if url in failed_urls else "ok"
        category = url_category(url)
        by_category.setdefault(category, []).append((index, title, url, status))

    lines = [
        "# Sportmonks Football API v3 — Catalogo pagine",
        "",
        f"> Generato: {generated_at}",
        f"> Fonte indice: {INDEX_URL}",
        f"> Sezione: {FOOTBALL_SECTION}",
        f"> Pagine totali: {len(urls)}",
        f"> Pagine scaricate con successo: {len(urls) - len(failed_urls)}",
        f"> Pagine fallite: {len(failed_urls)}",
        "",
        "Elenco completo delle pagine incluse nel bundle locale "
        "`docs/sportmonks-football-v3-docs.md`.",
        "",
        "Generato automaticamente da `scripts/fetch_sportmonks_docs.py`.",
        "Non modificare manualmente; rieseguire lo script per aggiornare.",
        "",
        "## Indice categorie",
        "",
    ]

    for category in sorted(by_category):
        count = len(by_category[category])
        anchor = category.replace("/", "-").replace(" ", "-")
        lines.append(f"- [{category}](#{anchor}) — {count} pagine")

    lines.extend(["", "## Dettaglio per categoria", ""])

    for category in sorted(by_category):
        anchor = category.replace("/", "-").replace(" ", "-")
        entries = by_category[category]
        lines.append(f"### {category}")
        lines.append("")
        lines.append(f"**{len(entries)} pagine**")
        lines.append("")
        lines.append("| # | Titolo | URL | Stato |")
        lines.append("|---|--------|-----|-------|")
        for index, title, url, status in entries:
            safe_title = title.replace("|", "\\|")
            lines.append(f"| {index} | {safe_title} | `{url}` | {status} |")
        lines.append("")

    if failed_urls:
        lines.extend(["## Pagine non scaricate", ""])
        for url, error in failures or []:
            title = titles.get(url, url)
            lines.append(f"- **{title}**: `{url}` — {error}")
        lines.append("")

    lines.extend(
        [
            "## Pagine escluse dal bundle",
            "",
            "Il bundle include **solo** la sezione *Football API 3.0* di `llms.txt`.",
            "Sono escluse automaticamente le API:",
            "",
            "- Motorsport API",
            "- Odds API",
            "- Core API",
            "- Football Widgets",
            "- Beta documentation",
            "",
            "Filtro implementato in `is_football_v3_url()` nello script di fetch.",
            "",
        ]
    )

    catalog_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return catalog_path


def build_header(url_count: int) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        "# Sportmonks Football API v3 — Local Documentation Bundle\n\n"
        f"> Generated at: {generated_at}\n"
        f"> Source index: {INDEX_URL}\n"
        f"> Pages included: {url_count}\n\n"
        "This file is auto-generated by `scripts/fetch_sportmonks_docs.py`.\n"
        "Do not edit manually; re-run the script to refresh the content.\n"
    )


def write_index(docs_dir: Path, index_text: str) -> Path:
    index_path = docs_dir / "sportmonks-llms-index.md"
    header = (
        "# Sportmonks llms.txt Index\n\n"
        f"> Source: {INDEX_URL}\n"
        f"> Saved at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    )
    index_path.write_text(header + index_text, encoding="utf-8")
    return index_path


def write_bundle(
    docs_dir: Path,
    urls: list[str],
    client: HttpClient,
) -> tuple[Path, list[str], list[tuple[str, str]]]:
    bundle_path = docs_dir / "sportmonks-football-v3-docs.md"
    parts: list[str] = [build_header(len(urls))]
    failures: list[tuple[str, str]] = []

    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] Fetching {url}")
        try:
            content = client.get_text(url).strip()
            parts.append(f"<!-- Source: {url} -->\n\n{content}")
        except RuntimeError as exc:
            message = str(exc)
            failures.append((url, message))
            print(f"  ! Skipped: {message}", file=sys.stderr)
            parts.append(
                f"<!-- Source: {url} -->\n\n"
                f"<!-- Fetch failed: {message} -->\n"
            )

        if index < len(urls):
            parts.append(PAGE_SEPARATOR.strip("\n"))

        time.sleep(REQUEST_DELAY_SECONDS)

    bundle_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return bundle_path, urls, failures


def _load_index_text(docs_dir: Path, client: HttpClient) -> str:
    index_path = docs_dir / "sportmonks-llms-index.md"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        if "## Football API 3.0" in content:
            print(f"Using local index {index_path}")
            return content

    print(f"Downloading index from {INDEX_URL}")
    index_text = client.get_text(INDEX_URL)
    write_index(docs_dir, index_text)
    return index_text


def _urls_from_bundle(docs_dir: Path) -> list[str]:
    bundle_path = docs_dir / "sportmonks-football-v3-docs.md"
    if not bundle_path.exists():
        return []
    pattern = re.compile(r"<!-- Source: (https://docs\.sportmonks\.com/v3/[^\s]+) -->")
    return pattern.findall(bundle_path.read_text(encoding="utf-8"))


def main() -> int:
    catalog_only = "--catalog-only" in sys.argv
    root = project_root()
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    client = HttpClient()
    index_text = _load_index_text(docs_dir, client)

    urls = extract_urls_from_section(index_text)
    if not urls:
        print("No Football API v3 markdown URLs found in index.", file=sys.stderr)
        return 1

    if catalog_only:
        bundle_urls = _urls_from_bundle(docs_dir)
        catalog_urls = bundle_urls if bundle_urls else urls
        catalog_path = write_pages_catalog(docs_dir, catalog_urls, index_text)
        print(f"Catalog written: {catalog_path} ({len(catalog_urls)} pages)")
        return 0

    print(f"Index ready at {docs_dir / 'sportmonks-llms-index.md'}")

    print(f"Found {len(urls)} Football API v3 pages to download")
    bundle_path, downloaded_urls, failures = write_bundle(docs_dir, urls, client)
    catalog_path = write_pages_catalog(docs_dir, downloaded_urls, index_text, failures)

    print()
    print("Done.")
    print(f"  Bundle: {bundle_path}")
    print(f"  Catalog: {catalog_path}")
    print(f"  Pages attempted: {len(downloaded_urls)}")
    print(f"  Failures: {len(failures)}")

    if failures:
        print("\nFailed URLs:", file=sys.stderr)
        for url, error in failures:
            print(f"  - {url}: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
