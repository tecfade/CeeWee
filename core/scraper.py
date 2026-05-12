from typing import Optional

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
