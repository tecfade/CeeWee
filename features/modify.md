# Feature: Nachträgliche Dokumentänderung (`modify.py`)

## Beschreibung

CeeWee generiert CV und Anschreiben bisher ausschließlich als kompletten
Neulauf aus den Markdown-Quelldaten in `cv/`. Dieses Feature ergänzt ein neues,
eigenständiges CLI-Kommando `modify.py`, mit dem ein frei formulierter
Änderungswunsch auf ein **bereits generiertes** Dokument angewendet werden
kann, ohne die gesamte Generierung erneut anzustoßen.

`modify.py` nimmt per `--cv` oder `--cover` (sich gegenseitig ausschließend,
genau eine Angabe erforderlich) entgegen, welches Dokument geändert werden
soll, sucht dazu automatisch die zuletzt generierte Quelldatei
(`output/cv_*.typ`/`.html` bzw. `output/cover_*.typ`/`.html`, unabhängig von
Firmenname/Engine des jeweils letzten Laufs) und wendet den per `--change`
übergebenen Freitext-Änderungswunsch darauf an, z. B.:

```bash
python modify.py --cv --change "ändere die Akzentfarbe von Blau zu Grün, ändere die Überschrift von X zu Y"
```

Die Engine (Typst/HTML) ergibt sich automatisch aus der Dateiendung der
gefundenen Quelldatei — kein separates `--engine`-Flag nötig. Ebenso werden die
Zielformate (PDF/DOCX) automatisch aus den vorhandenen Geschwisterdateien des
Originals übernommen (kein `--format`-Flag) — es wird immer "im selben Format
wie das Original" gerendert.

Nach der Änderung wird das Ergebnis unter einem neuen Zeitstempel im selben
Namensschema wie das Original gespeichert (Präfix und ggf. Firmen-Slug bleiben
erhalten, nur der Zeitstempel wird ersetzt) und in die ermittelten Zielformate
konvertiert. Das Original bleibt unverändert im `output/`-Verzeichnis erhalten.

Ein optionaler Parameter `--row ZEILE` gibt die Zeilennummer im Engine-Format-
Quelltext an, auf die sich die Änderung besonders bezieht. Er ist aktuell rein
unterstützend (wird als zusätzlicher Kontext an Claude durchgereicht) und dient
vor allem als Vorbereitung für eine später geplante grafische Oberfläche, die
gezielt auf einzelne Zeilen zeigen können soll.

Es wird bewusst **kein** Diff-/Patch-Mechanismus verfolgt (Claude bekommt das
volle Dokument und gibt das volle aktualisierte Dokument zurück) — konsistent
mit `generate_cv()`/`generate_cover_letter()`, und die bestehende
Design-Werte-Konvention (`#let accent = …`/`--accent-color: …`) bleibt dadurch
automatisch erhalten, ohne dass ein Patch-Parser nötig wäre.

Anders als bei `generate.py` (wo weder `--cv` noch `--cover` "beide"
bedeutet) ist bei `modify.py` genau eine der beiden Optionen **verpflichtend**:
Ein einzelner Änderungswunsch ist i. d. R. nur für eines der beiden strukturell
unterschiedlichen Dokumente sinnvoll formuliert.

## Voraussetzungen

- **Kein bestehender Mechanismus, um "das zuletzt generierte Dokument" zu
  einem Präfix zu finden**: `core/converter.py` kennt nur `new_timestamp()`
  und `slugify_company()`, aber keine Funktion, die `output/` nach dem
  neuesten `cv_*`/`cover_*` durchsucht. Muss neu gebaut werden — der
  Zeitstempel im Dateinamen (`YYYY-MM-DD_HH-MM-SS`) sortiert bereits als
  String korrekt chronologisch, ein Glob + Regex-Extraktion reicht.
- **Neuer, engine-agnostischer Agent-Prompt** `agents/modify.md` (anders als
  bei CV/Cover kein separates Typst-/HTML-Pärchen nötig, da die Aufgabe
  strukturell identisch ist und die Engine bereits durch den Eingabe-Quelltext
  vorgegeben ist). Muss die bestehende Design-Werte-Konvention
  (`#let accent = rgb("#RRGGBB")`/`font:` bzw. `--accent-color`/
  `--font-family`) explizit als "bleibt erhalten"-Regel enthalten, sonst
  könnte eine Farb-/Font-Änderung die maschinelle Auslesbarkeit brechen, auf
  die `_extract_design_tokens()` angewiesen ist.
- **`core/agent.py`** braucht eine neue Funktion `modify_document(source,
  change, engine, row=None, api_key=None) -> str`, analog zu `generate_cv()`/
  `generate_cover_letter()` (eigener Anthropic-Client, zweiteilige
  User-Message mit `cache_control` auf dem Bulk-Teil, System-Prompt aus
  `agents/modify.md`).
- **`core/converter.py`** braucht zwei weitere Helper neben
  `find_latest_source()`: `sibling_formats(source_path) -> list[str]` (prüft,
  ob `<stem>.pdf`/`<stem>.docx` neben der Quelldatei existieren) und
  `next_stem(old_stem) -> str` (ersetzt den Zeitstempel-Teil eines
  bestehenden Stems durch einen neuen, Präfix/Firmen-Infix bleiben
  unverändert).
- **Neues Skript `modify.py`** als zweiter CLI-Einstiegspunkt neben
  `generate.py` — schlanker, da kein Laden von `cv/`-Daten nötig ist (nur
  Ausgabeverzeichnis + Agent-Aufruf).
- **`CLAUDE.md`/`README.md`** müssen den neuen Befehl dokumentieren.

## Steps

1. `core/converter.py` ergänzen:
   - `_TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")`
     als Modul-Konstante.
   - `find_latest_source(output_dir: Path, prefix: str) -> Optional[Path]` —
     glob nach `f"{prefix}_*.typ"` und `f"{prefix}_*.html"`, `max()` nach dem
     per Regex extrahierten Zeitstempel-String (sortiert korrekt
     chronologisch), `None` falls nichts gefunden.
   - `sibling_formats(source_path: Path) -> list[str]` — prüft Existenz von
     `<stem>.pdf`/`<stem>.docx` im selben Verzeichnis, gibt die vorhandenen
     als Liste zurück.
   - `next_stem(old_stem: str) -> str` — ersetzt den (einen) per
     `_TIMESTAMP_PATTERN` gefundenen Zeitstempel im Stem durch einen frisch
     erzeugten (`new_timestamp()`), Fallback (Zeitstempel nicht gefunden):
     neuen Zeitstempel anhängen statt zu crashen.
2. `agents/modify.md` anlegen (Frontmatter `name: document-modifier`,
   `description`, `model: claude-opus-4-7`). Body: nimmt vollständiges
   Typst-/HTML-Dokument + Änderungswunsch entgegen, gibt **vollständiges**
   aktualisiertes Dokument zurück (kein Diff). Enthält:
   - Anweisung, nur die gewünschten Änderungen umzusetzen, Rest unverändert
     zu lassen.
   - Hinweis, bei referenzierter Zeile (per `--row`) diese als primären
     Ansatzpunkt zu nehmen, aber Konsistenz an anderen Stellen zu prüfen
     (z. B. wiederholte Farbwerte).
   - Design-Werte-Konvention als bindende Regel (Typst:
     `#let accent = rgb("#RRGGBB")`/`font:`; HTML: `--accent-color`/
     `--font-family`) — bleibt bei Änderungen erhalten und wird im Rest des
     Dokuments weiter per Referenz verwendet, nicht neu hart kodiert.
   - `## Ausgaberegeln — bindend`: ausschließlich valides Markup in der
     Syntax des Eingabedokuments, keine Code-Fences, keine Erklärung der
     Änderungen im Output.
3. `core/agent.py` ergänzen:
   - `_modify_meta, _MODIFY_SYSTEM_PROMPT = _load_agent("modify.md")` beim
     Modul-Import laden (Zeile analog zu den bestehenden fünf `_load_agent`-
     Aufrufen).
   - Neue Funktion `modify_document(source: str, change: str, engine: str,
     row: Optional[int] = None, api_key: Optional[str] = None) -> str`:
     baut `change_block` aus `## Änderungswunsch\n\n{change}`, ergänzt bei
     gesetztem `row` (und gültigem Bereich `1 <= row <= len(source.splitlines())`)
     die referenzierte Zeile als Zitat; sendet Quelltext als ersten
     User-Message-Teil mit `cache_control: ephemeral`, `change_block` als
     zweiten (uncached), System-Prompt `_MODIFY_SYSTEM_PROMPT` (gecached),
     `max_tokens=8096`. Gibt `response.content[0].text` zurück.
4. `modify.py` neu anlegen (voller CLI-Einstiegspunkt, analog `generate.py`):
   - Docstring mit Nutzungsbeispielen, `_require_api_key()` (identische
     Kopie wie in `generate.py`).
   - Argparse: `add_mutually_exclusive_group(required=True)` mit `--cv`/
     `--cover` (`store_true`); `--change` (`type=str`, `required=True`);
     `--row` (`type=int`, optional); `--output` (`type=Path`, Standard
     `BASE_DIR / "output"`, wie bei `generate.py`).
   - Ablauf: `prefix = "cv" if args.cv else "cover"` →
     `find_latest_source(args.output, prefix)` (kein Treffer → `sys.exit()`
     mit Hinweis, erst `generate.py --{prefix}` auszuführen) → Engine aus
     `source_path.suffix` ableiten (`.typ` → `"typst"`, sonst `"html"`) →
     `formats = sibling_formats(source_path)` → Quelltext lesen →
     `modify_document(source=..., change=args.change, engine=engine,
     row=args.row)` → `next_stem(source_path.stem)` →
     `convert(updated_source, args.output, formats, engine=engine,
     prefix=prefix, stem=new_stem)`.
5. `CLAUDE.md` aktualisieren:
   - Verzeichnisstruktur: `modify.py` und `agents/modify.md` ergänzen.
   - Neuer kurzer Abschnitt (z. B. unter "Generierungsablauf" oder als
     eigener Abschnitt "Nachträgliche Änderungen") analog zur bestehenden
     Beschreibung von `--match-style`: Zweck, Quelldatei-Auswahl (immer die
     zuletzt generierte), Namensschema-Fortführung.
   - Build-Abschnitt: `python modify.py --cv --change "…"`-Beispiel ergänzen.
6. `README.md` aktualisieren: Usage-Block um ein `modify.py`-Beispiel
   ergänzen, analog zum bestehenden `--match-style`-Beispiel.
7. Manuell testen (kein automatisiertes Testsetup im Projekt):
   - `python generate.py --cv` (Typst) → `python modify.py --cv --change
     "ändere die Akzentfarbe von Blau zu Grün"` — neue `.typ`/`.pdf` mit
     aktuellem Zeitstempel, Original bleibt erhalten, Akzentfarbe im neuen
     Dokument tatsächlich geändert.
   - Vorheriger Lauf mit `--target` (Firmen-Slug im Dateinamen) → nach
     `modify.py` bleibt der Firmen-Slug im neuen Dateinamen erhalten.
   - `python modify.py --cover --change "…" --row 12` — Konsolenausgabe/
     Ergebnis prüfen, dass die referenzierte Zeile sinnvoll berücksichtigt
     wurde.
   - `python generate.py --engine html --cover --format html pdf docx` →
     `modify.py --cover --change "…"` — alle drei Formate (inkl. DOCX)
     werden neu erzeugt, da alle drei als Geschwisterdateien vorlagen.
   - Leeres `output/`-Verzeichnis (oder falscher `--output`-Pfad) →
     verständliche Fehlermeldung statt Crash.
   - Weder `--cv` noch `--cover`, oder beide gleichzeitig → argparse-Fehler
     durch die `mutually_exclusive_group(required=True)`.
