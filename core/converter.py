import re
import shutil
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional


def new_timestamp() -> str:
    """Zeitstempel für einen Generierungslauf — von generate.py einmalig erzeugt und für CV und Anschreiben geteilt."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


_UMLAUT_MAP = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
})


def slugify_company(name: Optional[str], max_length: int = 30) -> Optional[str]:
    """Wandelt einen Unternehmensnamen in ein dateinamensicheres Segment um (für den Ausgabe-Dateinamen)."""
    if not name:
        return None

    text = name.translate(_UMLAUT_MAP)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    if not text:
        return None

    if len(text) > max_length:
        text = text[:max_length].rsplit("-", 1)[0].strip("-") or text[:max_length]

    return text or None


def _stem(prefix: str = "cv") -> str:
    return f"{prefix}_{new_timestamp()}"


_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")


def find_latest_source(output_dir: Path, prefix: str) -> Optional[Path]:
    """Findet die zuletzt generierte cv_/cover_-Quelldatei (.typ oder .html) im Ausgabeverzeichnis."""
    candidates = list(output_dir.glob(f"{prefix}_*.typ")) + list(output_dir.glob(f"{prefix}_*.html"))
    if not candidates:
        return None

    def sort_key(path: Path) -> str:
        match = _TIMESTAMP_PATTERN.search(path.stem)
        return match.group(0) if match else ""

    return max(candidates, key=sort_key)


def sibling_formats(source_path: Path) -> list[str]:
    """Ermittelt anhand vorhandener Geschwisterdateien, welche Zusatzformate (pdf/docx) neben der Quelldatei erzeugt wurden."""
    stem = source_path.stem
    formats = []
    if (source_path.parent / f"{stem}.pdf").exists():
        formats.append("pdf")
    if (source_path.parent / f"{stem}.docx").exists():
        formats.append("docx")
    return formats


def next_stem(old_stem: str) -> str:
    """Ersetzt den Zeitstempel eines bestehenden Stems durch einen neuen — Präfix und Firmen-Infix bleiben erhalten."""
    ts = new_timestamp()
    new_stem, count = _TIMESTAMP_PATTERN.subn(ts, old_stem)
    return new_stem if count else f"{old_stem}_{ts}"


# ── Typst ─────────────────────────────────────────────────────────────────────

def save_typst(source: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    print(f"  Typst → {path}")


def typst_to_pdf(typ_path: Path, pdf_path: Path) -> None:
    if not shutil.which("typst"):
        raise SystemExit(
            "Typst ist nicht installiert.\n"
            "Installieren mit: sudo pacman -S typst  (Arch)\n"
            "                  snap install typst     (Ubuntu)\n"
            "                  brew install typst     (macOS)\n"
            "                  winget install typst   (Windows)"
        )
    result = subprocess.run(
        ["typst", "compile", str(typ_path), str(pdf_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"Typst-Fehler:\n{result.stderr}")
    print(f"  PDF   → {pdf_path}")


# ── HTML / WeasyPrint ─────────────────────────────────────────────────────────

def save_html(source: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    print(f"  HTML  → {path}")


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError:
        raise SystemExit(
            "WeasyPrint ist nicht installiert.\n"
            "Installieren mit: pip install weasyprint"
        )
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    print(f"  PDF   → {pdf_path}")


def html_to_docx(html_path: Path, docx_path: Path) -> None:
    if not shutil.which("pandoc"):
        raise SystemExit(
            "Pandoc ist nicht installiert.\n"
            "Installieren mit: sudo pacman -S pandoc  (Arch)\n"
            "                  sudo apt install pandoc (Ubuntu)\n"
            "                  brew install pandoc     (macOS)\n"
            "                  winget install pandoc   (Windows)"
        )
    subprocess.run(["pandoc", str(html_path), "-o", str(docx_path)], check=True)
    print(f"  DOCX  → {docx_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def convert(
    source: str,
    output_dir: Path,
    formats: list[str],
    engine: str = "typst",
    prefix: str = "cv",
    stem: Optional[str] = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or _stem(prefix)

    if engine == "typst":
        typ_path = output_dir / f"{stem}.typ"
        save_typst(source, typ_path)
        if "pdf" in formats:
            typst_to_pdf(typ_path, output_dir / f"{stem}.pdf")
    else:
        html_path = output_dir / f"{stem}.html"
        save_html(source, html_path)
        if "pdf" in formats:
            html_to_pdf(html_path, output_dir / f"{stem}.pdf")
        if "docx" in formats:
            html_to_docx(html_path, output_dir / f"{stem}.docx")
