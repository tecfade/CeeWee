## Beschreibung

KI-gestützter Lebenslauf-Generator: Strukturierte CV-Daten aus Markdown-Dateien werden per Anthropic API an Claude gesendet, der daraus ein druckfertiges Dokument generiert (Typst oder HTML), das anschließend nach PDF/DOCX konvertiert wird.

## Ziele

- CV-Inhalte modular in einzelnen Markdown-Dateien mit YAML-Frontmatter pflegen
- Automatische Generierung via Claude API (claude-opus-4-7)
- Ausgabe nach PDF (via Typst oder WeasyPrint) und DOCX (via Pandoc)
- Optionales Job-Tailoring: CV an konkrete Stellenanzeige anpassen

## Verzeichnisstruktur

```
CeeWee/
├── agents/                    # System-Prompts für Claude-Agenten (Markdown + YAML-Frontmatter)
│   ├── cv-typst.md            # Prompt: CV als Typst-Dokument generieren
│   ├── cv-html.md             # Prompt: CV als HTML generieren
│   └── job-analyzer.md        # Prompt: Stellenanzeige strukturiert analysieren
├── core/
│   ├── agent.py               # Claude-API-Aufrufe (generate_cv, analyze_job_posting)
│   ├── loader.py              # Markdown-Dateien laden (Projekte, Arbeitgeber, Summary)
│   ├── converter.py           # Ausgabe speichern und nach PDF/DOCX konvertieren
│   └── scraper.py             # Stellenanzeigen von URLs abrufen
├── cv/                        # Eigene CV-Daten
│   ├── summary.md             # Kandidaten-Profil / Kurzvorstellung
│   ├── employers.md           # Arbeitgeber-Liste (YAML-Frontmatter: eintraege: […])
│   ├── skills.md              # Skill-Gruppen (YAML-Frontmatter: gruppen: […])
│   ├── projects/              # Berufliche Projekte
│   │   ├── [projektname].md   # Standalone-Projekt
│   │   └── [Gruppe]/          # Projekt-Gruppe
│   │       ├── _parent.md     # Gruppen-Metadaten und Überblick
│   │       └── [teilprojekt].md
│   └── hobby_projects/        # Eigene / Open-Source-Projekte
├── cv_example/                # Beispieldaten (anonymisiert, zur Orientierung)
├── output/                    # Generierte Ausgaben (nicht eingecheckt)
│   └── cv_YYYY-MM-DD_HH-MM-SS.{typ,pdf,html,docx}
├── generate.py                # CLI-Einstiegspunkt
├── requirements.txt
├── .env                       # ANTHROPIC_API_KEY (nicht eingecheckt)
└── .env.example
```

## Toolchain

- **Anthropic API / claude-opus-4-7** — CV-Generierung und Job-Analyse
- **Typst** (Standard) — Rendert `.typ`-Dokumente nach PDF
- **WeasyPrint** (alternativ, `--engine html`) — Rendert HTML nach PDF
- **Pandoc** — Konvertierung nach DOCX (nur mit `--engine html`)

## Generierungsablauf

1. `generate.py` lädt Projektdaten, Summary und Arbeitgeber aus `cv/`
2. Optional: Stellenanzeige per URL (`--target`) oder Datei (`--job-description`) abrufen und per Claude analysieren
3. Claude generiert ein vollständiges Typst- oder HTML-Dokument
4. `converter.py` speichert die Quelldatei und konvertiert nach PDF/DOCX

Der Claude-Aufruf in `core/agent.py` nutzt Prompt Caching (`cache_control: ephemeral`) für Projektdaten und System-Prompt.

## Frontmatter-Schema

### Projekte (`cv/projects/[name].md`)

```yaml
---
title: Projektname
zeitraum: "2023–2024"
rolle: "Backend-Entwickler"
arbeitgeber: Firmenname        # optional, verknüpft mit employers.md
technologien: [Python, Docker]
kunde: Kundenname              # optional
link: https://…                # optional
hervorheben: true              # ob das Projekt prominent erscheint
reihenfolge: 1                 # Sortierung (aufsteigend, Standard: 999)
---
```

### Projekt-Gruppen (`cv/projects/[Gruppe]/_parent.md`)

Gleiche Felder wie Standalone-Projekte. Unterprojekte im selben Verzeichnis erben den Kontext der Gruppe.

### Arbeitgeber (`cv/employers.md`)

```yaml
---
eintraege:
  - zeitraum: "Jan.2020–Jetzt"
    arbeitgeber: Firmenname
    rolle: Senior Software Engineer
---
```

### Skills (`cv/skills.md`)

```yaml
---
gruppen:
  - name: Programmiersprachen
    skills: [Python, JavaScript, TypeScript]
  - name: Frameworks
    skills: [React, FastAPI]
---
```

## Build

```bash
# Voraussetzungen
pip install -r requirements.txt
export ANTHROPIC_API_KEY='sk-ant-...'

# Generieren
python generate.py                              # Typst + PDF (Standard)
python generate.py --format pdf                 # nur PDF
python generate.py --format html pdf docx       # alle Formate
python generate.py --engine html                # HTML-Engine statt Typst

# Job-Tailoring
python generate.py --target https://company.com/jobs/xyz
python generate.py --job-description stelle.txt
```

Ausgaben landen als `output/cv_YYYY-MM-DD_HH-MM-SS.*` in `output/`.

## Sprache

CV-Inhalte: Deutsch. Code und Kommentare: Deutsch.
