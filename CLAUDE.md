## Beschreibung

KI-gestützter Lebenslauf- und Anschreiben-Generator: Strukturierte CV-Daten aus Markdown-Dateien werden per Anthropic API an Claude gesendet, der daraus ein druckfertiges Dokument generiert (Typst oder HTML), das anschließend nach PDF/DOCX konvertiert wird.

## Ziele

- CV-Inhalte modular in einzelnen Markdown-Dateien mit YAML-Frontmatter pflegen
- Automatische Generierung via Claude API (claude-opus-4-7)
- Ausgabe nach PDF (via Typst oder WeasyPrint) und DOCX (via Pandoc)
- Optionales Job-Tailoring: CV und Anschreiben an konkrete Stellenanzeige anpassen
- Wahlweise nur Lebenslauf (`--cv`), nur Anschreiben (`--cover`) oder beide (Standard) generieren — als zusammengehöriges Bewerbungspaket mit identischem Design
- Nachträgliche Änderungen an einem bereits generierten Dokument per `modify.py` (`--cv`/`--cover` + `--change`), ohne die komplette Generierung erneut anzustoßen

## Verzeichnisstruktur

```
CeeWee/
├── agents/                    # System-Prompts für Claude-Agenten (Markdown + YAML-Frontmatter)
│   ├── cv-typst.md            # Prompt: CV als Typst-Dokument generieren
│   ├── cv-html.md             # Prompt: CV als HTML generieren
│   ├── cover-typst.md         # Prompt: Anschreiben als Typst-Dokument generieren
│   ├── cover-html.md          # Prompt: Anschreiben als HTML generieren
│   ├── job-analyzer.md        # Prompt: Stellenanzeige strukturiert analysieren
│   └── modify.md              # Prompt: bestehendes Dokument gemäß Änderungswunsch aktualisieren
├── core/
│   ├── agent.py               # Claude-API-Aufrufe (generate_cv, generate_cover_letter, modify_document, analyze_job_posting)
│   ├── loader.py              # Markdown-Dateien laden (Projekte, Arbeitgeber, Summary, Kontakt, Anschreiben-Notizen)
│   ├── converter.py           # Ausgabe speichern und nach PDF/DOCX konvertieren
│   └── scraper.py             # Stellenanzeigen von URLs abrufen
├── cv/                        # Eigene CV-Daten
│   ├── contact.md             # Kontaktdaten (Name, E-Mail, Telefon, Adresse, Website, LinkedIn, GitHub)
│   ├── summary.md             # Kandidaten-Profil / Kurzvorstellung
│   ├── cover.md               # optional: Anschreiben-Entwurf/Eckpunkte (freier Body, analog zu summary.md)
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
│   ├── cv_[Unternehmen_]YYYY-MM-DD_HH-MM-SS.{typ,pdf,html,docx}
│   └── cover_[Unternehmen_]YYYY-MM-DD_HH-MM-SS.{typ,pdf,html,docx}   # gleicher Zeitstempel/Unternehmen wie zugehöriger CV
├── generate.py                # CLI-Einstiegspunkt
├── modify.py                  # CLI-Einstiegspunkt für nachträgliche Änderungen
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

1. `generate.py` lädt Projektdaten, Summary, Arbeitgeber, Kontakt und optional Anschreiben-Notizen aus `cv/`
2. Optional: Stellenanzeige per URL (`--target`) oder Datei (`--job-description`) abrufen und per Claude analysieren
3. `--cv` generiert nur den Lebenslauf, `--cover` nur das Anschreiben; ohne Angabe (oder mit beiden Flags) werden beide generiert
4. Claude generiert je Dokument ein vollständiges Typst- oder HTML-Dokument (`generate_cv` / `generate_cover_letter`)
5. `converter.py` speichert die Quelldatei(en) und konvertiert nach PDF/DOCX — CV und Anschreiben aus demselben Lauf erhalten denselben Zeitstempel-Stem (Präfix `cv_`/`cover_`). Wurde eine Stellenanzeige analysiert, wird der Unternehmensname (`job_analysis["unternehmen"]`) per `slugify_company()` dateinamensicher aufbereitet (Umlaute transliteriert, Sonderzeichen entfernt, auf 30 Zeichen gekürzt) und dem Zeitstempel vorangestellt.

Werden CV und Anschreiben im selben Lauf erzeugt, wird zuerst der CV generiert; die dort tatsächlich verwendete Akzentfarbe/Schriftart wird per `_extract_design_tokens()` aus dem generierten Dokument ausgelesen und dem Anschreiben-Agenten verbindlich vorgegeben (siehe Design-Werte-Konvention unten), damit beide Dokumente optisch als zusammengehöriges Bewerbungspaket wirken. Bei getrennten Läufen (`--cv` heute, `--cover` später) entfällt diese Garantie.

Optional kann per `--match-style` (setzt `--target` voraus) Akzentfarbe und Schriftcharakter (serif/sans-serif) der Stellenanzeigen-Zielseite übernommen werden, damit die generierten Unterlagen optisch an die Marke des potenziellen Arbeitgebers angelehnt sind. Die daraus gewonnenen Marken-Tokens sind der Ausgangswert für den CV; tatsächlich im generierten CV gelandete Design-Werte (via `_extract_design_tokens()`) haben weiterhin Vorrang für das Anschreiben.

Der Claude-Aufruf in `core/agent.py` nutzt Prompt Caching (`cache_control: ephemeral`) für Projektdaten und System-Prompt.

### Nachträgliche Änderungen (`modify.py`)

`modify.py --cv --change "…"` bzw. `modify.py --cover --change "…"` wendet einen frei formulierten Änderungswunsch auf das **zuletzt generierte** CV- bzw. Anschreiben-Dokument an (`find_latest_source()` sucht die neueste `cv_*`/`cover_*`-Quelldatei in `output/`, unabhängig von Engine oder Unternehmen). Engine (Typst/HTML) und Zielformate (PDF/DOCX) werden automatisch aus der gefundenen Datei bzw. ihren Geschwisterdateien übernommen — kein `--engine`-/`--format`-Flag nötig. `modify_document()` schickt das vollständige Dokument plus Änderungswunsch an Claude (Prompt `agents/modify.md`) und erhält das vollständige aktualisierte Dokument zurück (kein Diff/Patch). Das Ergebnis wird per `next_stem()` unter einem neuen Zeitstempel gespeichert — Präfix und ggf. Unternehmens-Slug aus dem Original bleiben erhalten, das Original selbst bleibt unverändert bestehen. Optional kann `--row` eine Zeilennummer im Engine-Quelltext angeben, auf die sich die Änderung besonders bezieht (auch als Vorbereitung für eine spätere grafische Oberfläche gedacht).

### Design-Werte-Konvention

Die CV- und Anschreiben-Agenten (`cv-typst.md`, `cv-html.md`, `cover-typst.md`, `cover-html.md`) müssen die verwendete Akzentfarbe und Schriftart maschinell auslesbar im generierten Dokument hinterlegen:

- **Typst**: genau eine `#let accent = rgb("#RRGGBB")`-Definition nahe dem Dokumentanfang, genau eine `font:`-Angabe im initialen `#set text(...)`
- **HTML**: CSS-Custom-Properties `--accent-color` und `--font-family` im `:root { … }` des `<style>`-Blocks

Werden dem Anschreiben-Agenten konkrete Design-Werte mitgegeben (aus dem zuvor generierten CV), sind exakt diese zu verwenden statt eigene zu interpretieren.

## Frontmatter-Schema

### Kontaktdaten (`cv/contact.md`)

```yaml
---
name: Vorname Nachname
email: name@example.com
telefon: "+49 151 12345678"    # optional
adresse: "Straße 1, PLZ Ort"   # optional
website: https://…             # optional
linkedin: https://…            # optional
github: https://…              # optional
---
```

Alle Felder außer `name` sind optional. Nicht gesetzte Felder erscheinen nicht im generierten Lebenslauf (keine Platzhalter).

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

### Anschreiben-Notizen (`cv/cover.md`, optional)

Analog zu `summary.md`: freier Markdown-Body (Frontmatter optional), den Claude als Grundlage für die Formulierung nutzt — z. B. bevorzugte Kernargumente, Tonalität, Punkte, die immer erwähnt werden sollen. Existiert die Datei nicht, generiert Claude das Anschreiben eigenständig aus Profil, Werdegang und ggf. `job_analysis`.

```yaml
---
headline: Anschreiben-Notizen
---

Freitext mit Eckpunkten, die im Anschreiben berücksichtigt werden sollen …
```

## Build

```bash
# Voraussetzungen
pip install -r requirements.txt
export ANTHROPIC_API_KEY='sk-ant-...'

# Generieren
python generate.py                              # Typst + PDF (Standard) — CV UND Anschreiben
python generate.py --format pdf                 # nur PDF
python generate.py --format html pdf docx       # alle Formate
python generate.py --engine html                # HTML-Engine statt Typst

# Nur eines der beiden Dokumente
python generate.py --cv                         # nur Lebenslauf
python generate.py --cover                      # nur Anschreiben

# Job-Tailoring (gilt für CV und Anschreiben)
python generate.py --target https://company.com/jobs/xyz
python generate.py --job-description stelle.txt
python generate.py --cover --target https://company.com/jobs/xyz

# Nachträgliche Änderung am zuletzt generierten Dokument
python modify.py --cv --change "ändere die Akzentfarbe von Blau zu Grün"
python modify.py --cover --change "kürze den zweiten Absatz" --row 42
```

Ausgaben landen als `output/cv_[Unternehmen_]YYYY-MM-DD_HH-MM-SS.*` bzw. `output/cover_[Unternehmen_]YYYY-MM-DD_HH-MM-SS.*` in `output/`. CV und Anschreiben aus demselben Lauf teilen sich den Zeitstempel-Stem; der Unternehmensname wird nur bei erfolgreicher Stellenanzeigen-Analyse (`--target`/`--job-description`) ergänzt.

## Sprache

CV-Inhalte: Deutsch. Code und Kommentare: Deutsch.
