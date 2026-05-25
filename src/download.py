"""Download data from RBA, ABS, and ATO sources."""

from pathlib import Path
from html.parser import HTMLParser
from typing import Optional
import urllib.request
import urllib.parse
import csv

import pandas as pd
import requests

from .config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    RBA_FILES,
    SOURCE_PAGES,
    SourceFile,
)


class LinkParser(HTMLParser):
    """Extract href attributes from HTML page."""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, value in attrs:
                if attr == "href":
                    self.links.append(value)


def ensure_dirs() -> None:
    """Create data folders before writing raw files or processed outputs."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    Path("outputs/model_summaries").mkdir(parents=True, exist_ok=True)
    Path("outputs/figures").mkdir(parents=True, exist_ok=True)


def _download_bytes(url: str, timeout: int = 60) -> Optional[bytes]:
    """Download URL content using requests or urllib fallback. Returns None on error."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.read()
        except Exception as fallback_e:
            print(f"  ⚠ Could not download from {url}")
            print(f"    requests error: {e}")
            print(f"    urllib error: {fallback_e}")
            return None


def _get_excel_links_from_page(page_url: str) -> list[str]:
    """Extract Excel file links from an ABS/ATO page."""
    try:
        with urllib.request.urlopen(page_url, timeout=10) as response:
            html = response.read().decode("utf-8")
            parser = LinkParser()
            parser.feed(html)
            excel_links = [
                l
                for l in parser.links
                if l.endswith(".xlsx") or l.endswith(".xls")
            ]
            return excel_links
    except Exception as e:
        print(f"  ⚠ Could not scrape {page_url}: {e}")
        return []


def download_rba_file(source: SourceFile, overwrite: bool = False) -> Optional[Path]:
    """Download a single RBA file. Returns path on success, None on failure."""
    out_path = RAW_DATA_DIR / source.filename

    if out_path.exists() and not overwrite:
        return out_path

    content = _download_bytes(source.url)
    if content:
        out_path.write_bytes(content)
        return out_path

    return None


def download_rba_files(overwrite: bool = False) -> list[Path]:
    """Download the RBA files used for rates, credit, CPI and debt controls."""
    results = [
        download_rba_file(source, overwrite=overwrite) for source in RBA_FILES
    ]
    return [path for path in results if path is not None]


def download_abs_file(
    source_name: str,
    page_url: str,
    known_direct_url: Optional[str] = None,
    out_filename: Optional[str] = None,
    overwrite: bool = False,
) -> Optional[Path]:
    """Download ABS file with tiered strategy: direct URL → scraping → manual.

    Returns path on success, None if requires manual download.
    """
    if out_filename is None:
        out_filename = f"abs_{source_name}.xlsx"

    out_path = RAW_DATA_DIR / out_filename

    if out_path.exists() and not overwrite:
        return out_path

    # Tier 1: Try known direct URL
    if known_direct_url:
        print(f"  {source_name}: trying direct URL...", end=" ")
        content = _download_bytes(known_direct_url)
        if content:
            out_path.write_bytes(content)
            print("✓")
            return out_path

    # Tier 2: Scrape the page for Excel links
    print(f"  {source_name}: scraping page for Excel links...", end=" ")
    excel_links = _get_excel_links_from_page(page_url)

    if excel_links:
        first_link = excel_links[0]
        if not first_link.startswith("http"):
            first_link = "https://www.abs.gov.au" + first_link

        try:
            content = _download_bytes(first_link)
            if content:
                out_path.write_bytes(content)
                print(f"✓ ({len(excel_links)} files available)")
                return out_path
        except Exception as e:
            print(f"failed to download: {e}")

    # Tier 3: Manual instructions
    print("requires manual download")
    print(f"\n    Manual download required for: {source_name}")
    print(f"    Visit: {page_url}")
    print(f"    Save the Excel file to: {out_path}\n")

    return None


def download_abs_files(overwrite: bool = False) -> dict[str, Optional[Path]]:
    """Download ABS/ATO source files. Skip ATO (requires manual action)."""
    results = {}

    for source_name, page_url in SOURCE_PAGES.items():
        if "ato" in source_name:
            print(f"⏭️  {source_name}: ATO files require manual download")
            print(f"    Visit: {page_url}\n")
            results[source_name] = None
            continue

        print(f"📥 Downloading {source_name}...", end=" ")
        path = download_abs_file(source_name, page_url, overwrite=overwrite)
        results[source_name] = path
        if path:
            print(f"✓ ({path.name})")
        else:
            print("(manual action required)")

    return results


def write_source_pages() -> Path:
    """Write ABS/ATO source landing pages for manual and auditable downloads."""
    path = PROCESSED_DATA_DIR / "source_pages.csv"
    rows = [{"source_name": key, "url": value} for key, value in SOURCE_PAGES.items()]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def download_all(overwrite: bool = False) -> None:
    """Orchestrate download of all data sources."""
    print("\n📥 Housing Policy Analysis: Data Download\n")
    print("=" * 60)

    ensure_dirs()

    print("\n1️⃣  Downloading RBA files...")
    print("-" * 60)
    rba_paths = download_rba_files(overwrite=overwrite)
    print(f"\n✓ Downloaded {len(rba_paths)}/{len(RBA_FILES)} RBA files")

    print("\n2️⃣  Downloading ABS files...")
    print("-" * 60)
    abs_results = download_abs_files(overwrite=overwrite)
    abs_success = sum(1 for p in abs_results.values() if p is not None)
    abs_total = sum(1 for k in abs_results.keys() if "ato" not in k)
    print(f"\n✓ Downloaded {abs_success}/{abs_total} ABS files")

    print("\n3️⃣  Writing source pages reference...")
    print("-" * 60)
    source_page_path = write_source_pages()
    print(f"✓ Source pages written to: {source_page_path}")

    print("\n" + "=" * 60)
    print("📋 Download Summary")
    print("=" * 60)
    print(f"✓ RBA files: {len(rba_paths)}/{len(RBA_FILES)}")
    print(f"✓ ABS files: {abs_success}/{abs_total}")

    manual_abs = [k for k, v in abs_results.items() if v is None and "ato" not in k]
    if manual_abs:
        print(f"\n⚠️  {len(manual_abs)} ABS files require manual download:")
        for source in manual_abs:
            print(f"    - {source}")
        print(f"\n  See source_pages.csv for URLs")

    print(
        "\n✓ Ready for extraction. Run: python -c 'from src.extract import extract_quarterly; extract_quarterly()'\n"
    )
