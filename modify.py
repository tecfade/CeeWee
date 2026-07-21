#!/usr/bin/env python3
"""
CeeWee – Änderungen an bereits generierten CV-/Anschreiben-Dokumenten

Verwendung:
  python modify.py --cv --change "ändere die Akzentfarbe von Blau zu Grün"
  python modify.py --cover --change "kürze den zweiten Absatz" --row 42
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).parent


def _require_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "Fehler: ANTHROPIC_API_KEY ist nicht gesetzt.\n"
            "Exportiere den Key z. B. mit:\n"
            "  export ANTHROPIC_API_KEY='sk-ant-...'"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CeeWee – Änderungen an bereits generierten CV-/Anschreiben-Dokumenten",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--cv",
        action="store_true",
        help="Den zuletzt generierten Lebenslauf ändern",
    )
    target.add_argument(
        "--cover",
        action="store_true",
        help="Das zuletzt generierte Anschreiben ändern",
    )
    parser.add_argument(
        "--change",
        type=str,
        required=True,
        metavar="TEXT",
        help="Änderungswunsch in natürlicher Sprache, z. B. 'ändere die Akzentfarbe von Blau zu Grün'",
    )
    parser.add_argument(
        "--row",
        type=int,
        metavar="ZEILE",
        help="Zeilennummer im Engine-Format-Quelltext, auf die sich die Änderung besonders bezieht (optional)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "output",
        help="Ausgabeverzeichnis  (Standard: ./output)",
    )
    args = parser.parse_args()

    _require_api_key()

    from core.converter import convert, find_latest_source, sibling_formats, next_stem
    from core.agent import modify_document

    prefix = "cv" if args.cv else "cover"
    label = "Lebenslauf" if args.cv else "Anschreiben"

    source_path = find_latest_source(args.output, prefix)
    if source_path is None:
        sys.exit(
            f"Kein bestehendes {label}-Dokument in {args.output} gefunden.\n"
            f"Erst 'python generate.py --{prefix}' ausführen."
        )

    engine = "typst" if source_path.suffix == ".typ" else "html"
    formats = sibling_formats(source_path)

    print(f"Ändere {label}: {source_path.name}")
    source = source_path.read_text(encoding="utf-8")

    updated_source = modify_document(source=source, change=args.change, engine=engine, row=args.row)

    new_stem = next_stem(source_path.stem)
    convert(updated_source, args.output, formats, engine=engine, prefix=prefix, stem=new_stem)

    print("Fertig.")


if __name__ == "__main__":
    main()
