## Beschreibung

Dieses Projekt dient dazu, einen Lebenslauf (CV) aus einzelnen Markdown-Dateien zusammenzubauen und in mehrere Formate zu exportieren.

## Ziele

- CV-Inhalte modular in einzelnen Markdown-Dateien mit YAML-Frontmatter pflegen
- Automatischer Build nach PDF, Word (.docx) und HTML
- Projekte als eigenständige, wiederverwendbare Einheiten

## Verzeichnisstruktur

```
CeeWee/
├── projects/          # Einzelne Projekte: projects/[projektname].md
├── sections/          # CV-Abschnitte: Erfahrung, Ausbildung, Skills, Kontakt, …
├── education/         # Ausbildung
├── output/            # Generierte Ausgaben (nicht eingecheckt)
└── build.py           # Build-Orchestrator
```

## Toolchain

- **Claude Code (VS Code)** — Liest die Quelldateien und generiert den CV-Text on-demand
- **Pandoc** — Konvertierung des generierten Markdowns nach PDF, DOCX und HTML

## Generierungsansatz

Kein festes Templating, keine API-Integration. Stattdessen:

1. Daten in `projects/*.md` und `sections/*.md` pflegen
2. Claude Code in VS Code beauftragen, daraus einen CV zu generieren
3. Das Ergebnis als `output/cv.md` speichern
4. Pandoc konvertiert `output/cv.md` ins Zielformat

Ein `Makefile` oder kleines Shell-Skript übernimmt nur den Pandoc-Schritt.

## Frontmatter-Schema für Projekte (`projects/*.md`)

```yaml
---
title: Projektname
zeitraum: "2023–2024"
rolle: "Backend-Entwickler"
technologien: [Python, PostgreSQL, Docker]
kunde: Firmenname          # optional
link: https://…            # optional
hervorheben: true          # ob das Projekt in der Haupt-CV erscheint
---
```

Projektbeschreibung hier als Markdown-Text.

## Build

```bash
python build.py            # alle Formate generieren
python build.py --format pdf
python build.py --format html
python build.py --format docx
```

Ausgaben landen in `output/`.

## Sprache

Aktuell: Deutsch.
