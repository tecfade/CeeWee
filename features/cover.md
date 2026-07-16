# Feature: Anschreiben-Generierung

## Beschreibung

CeeWee generiert aktuell ausschließlich den Lebenslauf. Dieses Feature erweitert
den Generator um die Fähigkeit, zusätzlich (oder stattdessen) ein Anschreiben
(Cover Letter) zu erzeugen — analog zum bestehenden CV-Workflow: strukturierte
Daten aus `cv/` + optionaler Stellenanzeigen-Kontext → Claude API → druckfertiges
Dokument (Typst oder HTML) → PDF/DOCX.

Neue CLI-Optionen in `generate.py`:

- `--cv` — generiert nur den Lebenslauf
- `--cover` — generiert nur das Anschreiben
- keine der beiden Optionen — generiert **beide** Dokumente (Standardverhalten,
  abwärtskompatibel zum bisherigen Verhalten)
- beide Optionen zusammen — äquivalent zu keiner Angabe (beide werden generiert)

Lebenslauf und Anschreiben, die im selben Lauf entstehen, erhalten denselben
Zeitstempel-Stem (z. B. `cv_2026-07-16_10-30-00.pdf` und
`cover_2026-07-16_10-30-00.pdf`), damit ersichtlich ist, dass sie zusammengehören.

Ist beim Generieren eines Anschreibens keine Stellenanzeige bekannt (weder
`--target` noch `--job-description` angegeben), wird trotzdem ein Anschreiben
erzeugt — allgemein gehalten, mit generischer Motivation und Platzhaltern für
Firma/Position, nutzbar als Vorlage zum manuellen Anpassen.

Optional kann in `cv/cover.md` ein grober Anschreiben-Entwurf oder eine
Sammlung von Eckpunkten hinterlegt werden (freier Markdown-Text, analog zu
`cv/summary.md`), die Claude als Grundlage/Ausgangsmaterial für die
Formulierung nutzt (z. B. bevorzugte Kernargumente, Tonalität,
Punkte, die immer erwähnt werden sollen). Die Datei ist optional — existiert
sie nicht, generiert Claude das Anschreiben komplett eigenständig aus
Profil, Werdegang und ggf. `job_analysis`.

Werden CV und Anschreiben im selben Lauf erzeugt, müssen beide dasselbe
Farbschema (Akzentfarbe) und Text-Styling (Schriftart, Basis-Schriftgröße)
verwenden — sie sollen als zusammengehöriges Bewerbungspaket wirken, nicht
wie zwei unabhängig gestaltete Dokumente.

## Voraussetzungen

- **Neuer Agent-Prompt fürs Anschreiben**: Bisher existieren nur `cv-typst.md`,
  `cv-html.md` und `job-analyzer.md` in `agents/`. Es braucht analoge
  System-Prompts für die Anschreiben-Generierung (Aufbau nach DIN 5008,
  Anrede/Betreff/Einleitung/Hauptteil/Schluss, Bezug auf Stellenanzeige falls
  vorhanden, generische Motivation falls nicht).
- **Kontaktdaten werden aktuell nicht geladen**: `cv/contact.md` existiert
  (Name, E-Mail, Telefon, Adresse, LinkedIn) und wird bereits vom CV-Agenten
  implizit erwartet, aber in `generate.py`/`core/loader.py` gibt es noch keine
  `load_contact()`-Funktion. Fürs Anschreiben (Absenderzeile, Datum, Ort) ist
  das zwingend nötig — für den CV-Header wäre es ebenfalls sinnvoll,
  ist aber nicht Teil dieses Features.
- **`core/agent.py`** muss um eine `generate_cover_letter(...)`-Funktion
  erweitert werden, analog zu `generate_cv(...)`, mit eigenem System-Prompt
  (Typst/HTML je nach `--engine`) und Zugriff auf Kandidaten-Profil, Kontakt,
  ausgewählte/relevante Projekte sowie optional `job_analysis`.
- **`core/converter.py`** unterscheidet aktuell nicht zwischen CV- und
  Cover-Ausgabe (Dateiname-Präfix ist hart auf `cv_` gesetzt). Muss so
  erweitert werden, dass Präfix (`cv`/`cover`) und ein gemeinsam übergebener
  Zeitstempel-Stem unterstützt werden.
- Typst-Layout fürs Anschreiben unterscheidet sich strukturell vom
  CV-Layout (Fließtext statt Listen/Tabellen) — der neue Agent-Prompt muss
  eigene Typst-/HTML-Bausteine (Briefkopf, Datumszeile, Betreffzeile,
  Grußformel) vorgeben, ähnlich der Kurzreferenz in `cv-typst.md`.
- **`cv/cover.md`** (optional, analog zu `cv/summary.md`: Frontmatter +
  Freitext-Body) muss als neue Eingabequelle unterstützt werden. Existiert
  die Datei nicht, läuft die Generierung unverändert ohne diesen Zusatzinput.
- **Konsistentes Design zwischen CV und Anschreiben ist kein Selbstläufer**:
  Beide Dokumente entstehen über zwei unabhängige Claude-Aufrufe. Selbst
  wenn beide denselben `--design`-Freitext ("Akzentfarbe Dunkelblau")
  bekommen, kann jeder Aufruf einen leicht anderen Blauton oder eine andere
  Schriftart aus der Liste zulässiger Fonts wählen. Reines Wiederverwenden
  desselben Freitexts reicht daher **nicht** aus — es braucht konkrete,
  wiederverwendbare Design-Werte (Hex-Farbe, Schriftart) statt zweier
  unabhängiger Interpretationen derselben Beschreibung. Die Garantie gilt
  nur innerhalb **eines** Laufs, der beide Dokumente erzeugt — werden CV
  und Anschreiben in getrennten Aufrufen von `generate.py` generiert
  (z. B. `--cv` heute, `--cover` nächste Woche), gibt es keine Quelle zum
  Abgleichen und beide können optisch leicht auseinanderlaufen.

## Steps

1. `core/loader.py`:
   - `load_contact(base_dir)` ergänzen — parst `cv/contact.md`
     (Frontmatter: `name`, `email`, `telefon`, `adresse`, `linkedin`) und gibt
     ein dict zurück.
   - `load_cover_notes(base_dir)` ergänzen — parst `cv/cover.md` analog zu
     `load_summary()` (Frontmatter optional, gibt den Body-Text zurück oder
     `None` falls Datei fehlt/leer ist).
2. `agents/cv-typst.md` und `agents/cv-html.md` anpassen, damit die
   verwendeten Design-Werte in vorhersagbarer, maschinell auslesbarer Form
   im generierten Dokument stehen (neue bindende Ausgaberegel):
   - Typst: genau eine `#let accent = rgb("#RRGGBB")`-Definition nahe dem
     Dokumentanfang, genau eine `font:`-Angabe im initialen `#set text(...)`.
   - HTML: CSS-Custom-Properties `--accent-color` und `--font-family` im
     `:root { … }` des `<style>`-Blocks definieren und im Rest des Dokuments
     referenzieren statt Werte erneut hart zu kodieren.
3. `agents/cover-typst.md` und `agents/cover-html.md` anlegen: System-Prompts
   für die Anschreiben-Generierung (Frontmatter `name`, `description`, `model`
   analog zu den bestehenden Agenten). Inhalt: DIN-5008-Aufbau, Bezug auf
   `job_analysis` falls vorhanden (Unternehmen, Position, Keywords,
   Schwerpunkte aus dem Tailoring-Block wiederverwenden), sonst generische
   Formulierung mit Platzhaltern `[Firma]`/`[Position]`. Ausgaberegeln
   analog zu `cv-typst.md`/`cv-html.md` (nur valides Markup, keine
   Code-Fences, Deutsch, 1 DIN-A4-Seite) — inklusive derselben
   Design-Werte-Konvention aus Schritt 2, plus der Anweisung: **Werden
   konkrete Design-Vorgaben (Akzentfarbe, Schriftart) im User-Prompt
   mitgeliefert, sind exakt diese Werte zu verwenden statt eigene zu wählen.**
4. `core/agent.py`:
   - Neue Agenten beim Modul-Import laden (`_cover_typst_meta`,
     `_COVER_TYPST_SYSTEM_PROMPT`, analog für HTML).
   - `_extract_design_tokens(source: str, engine: str) -> dict` ergänzen:
     liest per Regex Akzentfarbe und Schriftart aus einem bereits
     generierten Dokument aus (Typst: `#let accent = rgb\("(#[0-9A-Fa-f]{6})"\)`
     / `font:\s*"([^"]+)"`; HTML: `--accent-color:\s*([^;]+);` /
     `--font-family:\s*([^;]+);`). Liefert `{}` falls nichts gefunden wird.
   - Neue Funktion `generate_cover_letter(contact, summary, employers,
     projects, design_prompt, engine, job_analysis=None, cover_notes=None,
     design_tokens=None, api_key=None)` analog zu `generate_cv`, die den
     Kontaktblock, das Kandidaten-Profil, relevante Berufserfahrung
     (verdichtet, keine volle Projektliste), optional den Tailoring-Block
     sowie optional `cover_notes` zusammenstellt und an Claude schickt.
     Ist `design_tokens` gesetzt (aus Schritt 4/`_extract_design_tokens`
     des bereits generierten CV), wird zusätzlich zum `design_prompt` ein
     verbindlicher Block angehängt, z. B. `"Verwende exakt: Akzentfarbe
     {accent}, Schriftart {font}"` — sonst interpretiert der Cover-Agent
     `design_prompt` eigenständig wie der CV-Agent.
   - Neuen `_build_contact_block(contact)`-Helper ergänzen.
5. `core/converter.py`: `convert()` um einen `prefix: str = "cv"`-Parameter
   und einen optionalen `stem: Optional[str] = None`-Parameter erweitern
   (Stem-Berechnung aus `_stem()` extrahieren, damit `generate.py` denselben
   Zeitstempel für CV und Cover übergeben kann).
6. `generate.py`:
   - CLI-Argumente `--cv` und `--cover` ergänzen (`action="store_true"`).
   - Nach dem Parsen: `generate_both = not args.cv and not args.cover` (deckt
     auch den Fall ab, dass beide gesetzt sind — dann werden ohnehin beide
     generiert, keine explizite Fehlerbehandlung nötig).
   - `load_contact(CV_DIR)` und `load_cover_notes(CV_DIR)` in den Ladeblock
     aufnehmen (Cover-Notizen nur, wenn `--cover` bzw. der Default-Modus
     greift).
   - Gemeinsamen Zeitstempel-Stem einmal pro Lauf erzeugen und an `convert()`
     für CV und Cover durchreichen.
   - **Reihenfolge bei `generate_both`**: CV zuerst generieren, per
     `_extract_design_tokens(cv_source, engine)` die tatsächlich verwendeten
     Werte auslesen und diese an `generate_cover_letter(..., design_tokens=…)`
     durchreichen, damit das Anschreiben exakt dieselbe Akzentfarbe/Schriftart
     übernimmt statt sie neu zu interpretieren. Wird nur `--cover` verlangt
     (kein CV in diesem Lauf), entfällt diese Quelle — der Cover-Agent
     interpretiert `--design` dann eigenständig (bekanntes, akzeptiertes
     Limit aus den Voraussetzungen).
   - Bedingt `generate_cv(...)` und/oder `generate_cover_letter(...)` aufrufen
     und jeweils mit passendem `prefix` konvertieren.
7. `CLAUDE.md` aktualisieren: Verzeichnisstruktur (`agents/cover-typst.md`,
   `agents/cover-html.md`, `cv/cover.md`), CLI-Beispiele (`--cv`, `--cover`),
   Frontmatter-Schema-Abschnitt für `cv/cover.md` (optional, freier Body wie
   bei `summary.md`) und Generierungsablauf-Abschnitt ergänzen (inkl. Hinweis
   auf die Design-Werte-Konvention aus Schritt 2/3).
8. Manuell testen: `--cv` allein, `--cover` allein (mit und ohne `--target`,
   mit und ohne `cv/cover.md`), kein Flag (beide, gemeinsamer Zeitstempel),
   beide Flags gleichzeitig — jeweils Typst- und HTML-Engine. Zusätzlich
   gezielt prüfen: bei `generate_both` haben CV und Anschreiben identische
   Akzentfarbe/Schriftart in den erzeugten `.typ`/`.html`-Quelldateien.
