#!/usr/bin/env python3
"""
CeeWee – KI-gestützter Lebenslauf-Generator

Verwendung:
  python generate.py
  python generate.py --format pdf
  python generate.py --format html pdf --design "minimalistisch, Akzentfarbe Dunkelblau"
  python generate.py --format pdf --target https://company.com/jobs/senior-frontend
  python generate.py --format pdf --job-description stellenanzeige.txt
  python generate.py --cv                          # nur Lebenslauf
  python generate.py --cover --target https://…     # nur Anschreiben, tailored
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).parent
CV_DIR = BASE_DIR / "cv"


def _require_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "Fehler: ANTHROPIC_API_KEY ist nicht gesetzt.\n"
            "Exportiere den Key z. B. mit:\n"
            "  export ANTHROPIC_API_KEY='sk-ant-...'"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CeeWee – KI-gestützter Lebenslauf-Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--format",
        nargs="+",
        choices=["html", "pdf", "docx"],
        default=["html", "pdf"],
        metavar="FORMAT",
        help="Ausgabeformat(e): html, pdf, docx  (Standard: html pdf)",
    )
    parser.add_argument(
        "--design",
        type=str,
        default="professionell, modern, minimalistisch, Akzentfarbe Dunkelblau",
        help="Design-Beschreibung für den Lebenslauf",
    )
    parser.add_argument(
        "--target",
        type=str,
        metavar="URL",
        help="URL einer Stellenanzeige für gezieltes Tailoring",
    )
    parser.add_argument(
        "--job-description",
        type=Path,
        metavar="DATEI",
        help="Lokale Textdatei mit Stellenbeschreibung (Fallback zu --target)",
    )
    parser.add_argument(
        "--engine",
        choices=["typst", "html"],
        default="typst",
        help="Render-Engine: typst (Standard, empfohlen) oder html (WeasyPrint)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "output",
        help="Ausgabeverzeichnis  (Standard: ./output)",
    )
    parser.add_argument(
        "--cv",
        action="store_true",
        help="Nur den Lebenslauf generieren",
    )
    parser.add_argument(
        "--cover",
        action="store_true",
        help="Nur das Anschreiben generieren",
    )
    args = parser.parse_args()

    _require_api_key()

    # Lazy imports — only after env check so errors are clear
    from core.loader import (
        load_projects, load_summary, load_employers, load_skills,
        load_contact, load_cover_notes,
    )
    from core.scraper import fetch_job_posting
    from core.agent import analyze_job_posting, generate_cv, generate_cover_letter, _extract_design_tokens
    from core.converter import convert, new_timestamp
    import anthropic

    generate_both = not args.cv and not args.cover
    want_cv = args.cv or generate_both
    want_cover = args.cover or generate_both

    # ── Load project data ────────────────────────────────────────────────────
    print("Lade Projektdaten …")
    projects = load_projects(CV_DIR / "projects")
    summary = load_summary(CV_DIR)
    print(f"  {len(projects)} Projekt(e) geladen")

    hobby_dir = CV_DIR / "hobby_projects"
    hobby_projects = load_projects(hobby_dir) if hobby_dir.exists() else []
    if hobby_projects:
        print(f"  {len(hobby_projects)} Hobby-Projekt(e) geladen")

    employers = load_employers(CV_DIR)
    if employers:
        print(f"  {len(employers)} Arbeitgeber geladen")

    skills = load_skills(CV_DIR)
    if skills:
        print(f"  {len(skills)} Skill-Gruppe(n) geladen")

    contact = load_contact(CV_DIR)
    if contact:
        print(f"  Kontaktdaten geladen ({contact.get('name', '–')})")
    cover_notes = load_cover_notes(CV_DIR) if want_cover else None

    # ── Optionally analyse job posting ───────────────────────────────────────
    job_analysis = None
    client = anthropic.Anthropic()

    if args.target:
        print(f"Analysiere Stellenanzeige: {args.target}")
        job_text = fetch_job_posting(args.target)
        if job_text:
            job_analysis = analyze_job_posting(client, job_text)
            if job_analysis:
                print(f"  Position  : {job_analysis.get('position')} @ {job_analysis.get('unternehmen')}")
                print(f"  Technologien: {', '.join(job_analysis.get('technologien', [])[:6])}")
            else:
                print("  Analyse fehlgeschlagen – generiere ohne Tailoring")
        else:
            print("  URL nicht abrufbar – generiere ohne Tailoring")

    elif args.job_description:
        if not args.job_description.exists():
            sys.exit(f"Datei nicht gefunden: {args.job_description}")
        print(f"Lese Stellenbeschreibung: {args.job_description}")
        job_analysis = analyze_job_posting(client, args.job_description.read_text(encoding="utf-8"))
        if job_analysis:
            print(f"  Position  : {job_analysis.get('position')} @ {job_analysis.get('unternehmen')}")
        else:
            print("  Analyse fehlgeschlagen – generiere ohne Tailoring")

    tailoring_note = f" (tailored für {job_analysis.get('unternehmen')})" if job_analysis else ""
    ts = new_timestamp()
    design_tokens = None

    # ── Generate CV ──────────────────────────────────────────────────────────
    if want_cv:
        print(f"Generiere Lebenslauf{tailoring_note} …")

        cv_source = generate_cv(
            projects=projects,
            summary=summary,
            design_prompt=args.design,
            engine=args.engine,
            hobby_projects=hobby_projects or None,
            employers=employers or None,
            skills=skills or None,
            contact=contact or None,
            job_analysis=job_analysis,
        )

        convert(cv_source, args.output, args.format, engine=args.engine, prefix="cv", stem=f"cv_{ts}")

        if want_cover:
            design_tokens = _extract_design_tokens(cv_source, args.engine)

    # ── Generate cover letter ────────────────────────────────────────────────
    if want_cover:
        print(f"Generiere Anschreiben{tailoring_note} …")

        cover_source = generate_cover_letter(
            contact=contact,
            summary=summary,
            employers=employers or None,
            projects=projects,
            design_prompt=args.design,
            engine=args.engine,
            job_analysis=job_analysis,
            cover_notes=cover_notes,
            design_tokens=design_tokens,
        )

        convert(cover_source, args.output, args.format, engine=args.engine, prefix="cover", stem=f"cover_{ts}")

    print("Fertig.")


if __name__ == "__main__":
    main()
