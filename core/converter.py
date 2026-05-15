import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def _stem(output_dir: Path) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"cv_{ts}"


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

def convert(source: str, output_dir: Path, formats: list[str], engine: str = "typst") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _stem(output_dir)

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
