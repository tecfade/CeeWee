import re
from collections import Counter
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Tags whose content is never useful for job analysis
_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]

_COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgb\([^)]+\)")
_FONT_FAMILY_PATTERN = re.compile(r"font-family\s*:\s*([^;}{]+)")
_MAX_STYLESHEET_BYTES = 50_000

# Pfad-Marker zur Priorisierung beim Fetch: generische Plugin-/Vendor-CSS enthält
# praktisch nie die tatsächliche Markenfarbe, Custom-/Child-Theme-CSS sehr häufig.
_GENERIC_STYLESHEET_MARKERS = ("/plugins/", "/vendor/", "/node_modules/")
_BRAND_STYLESHEET_MARKERS = ("custom", "dynamic", "child", "brand", "scheme")


def _stylesheet_priority(href: str) -> int:
    """Niedrigere Zahl = beim Fetch bevorzugt (0 = vermutlich markenspezifisch, 2 = generisch)."""
    href_lower = href.lower()
    if any(marker in href_lower for marker in _GENERIC_STYLESHEET_MARKERS):
        return 2
    if any(marker in href_lower for marker in _BRAND_STYLESHEET_MARKERS):
        return 0
    return 1


def fetch_job_posting(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch a URL and return the main text content, or None on failure."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  Fehler beim Abrufen der URL: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    # Prefer semantic content containers, fall back to <body>
    container = (
        soup.find("main")
        or soup.find(id="main-content")
        or soup.find(id="job-description")
        or soup.find(class_="job-description")
        or soup.find(class_="jobDescription")
        or soup.find("article")
        or soup.find("body")
    )

    if container is None:
        return None

    lines = [
        line.strip()
        for line in container.get_text(separator="\n").splitlines()
        if line.strip()
    ]
    return "\n".join(lines)


def fetch_style_signals(url: str, timeout: int = 15, max_stylesheets: int = 3) -> Optional[str]:
    """Fetch a URL and return a compact digest of colors/fonts used, or None on failure."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  Fehler beim Abrufen der URL: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    css_chunks = []

    theme_color_tag = soup.find("meta", attrs={"name": "theme-color"})
    if theme_color_tag and theme_color_tag.get("content"):
        css_chunks.append(theme_color_tag["content"])

    for style_tag in soup.find_all("style"):
        if style_tag.string:
            css_chunks.append(style_tag.string)

    stylesheet_links = [
        link.get("href")
        for link in soup.find_all("link", rel=lambda v: v and "stylesheet" in v.lower())
        if link.get("href")
    ]
    stylesheet_links = sorted(stylesheet_links, key=_stylesheet_priority)[:max_stylesheets]

    for href in stylesheet_links:
        stylesheet_url = urljoin(url, href)
        try:
            css_resp = requests.get(stylesheet_url, headers=_HEADERS, timeout=timeout)
            css_resp.raise_for_status()
        except requests.RequestException:
            continue
        css_chunks.append(css_resp.text[:_MAX_STYLESHEET_BYTES])

    css_text = "\n".join(css_chunks)
    if not css_text:
        return None

    colors = Counter(match.lower() for match in _COLOR_PATTERN.findall(css_text))
    fonts = Counter(match.strip() for match in _FONT_FAMILY_PATTERN.findall(css_text))

    if not colors and not fonts:
        return None

    digest_lines = []
    if colors:
        digest_lines.append("Farben (Häufigkeit):")
        for color, count in colors.most_common(20):
            digest_lines.append(f"- {color}: {count}")
    if fonts:
        digest_lines.append("font-family-Deklarationen (Häufigkeit):")
        for font, count in fonts.most_common(10):
            digest_lines.append(f"- {font}: {count}")

    return "\n".join(digest_lines)
