# Feature: Marken-Stilübernahme (`--match-style`)

## Beschreibung

CeeWee generiert CV und Anschreiben aktuell mit einer frei formulierten
Design-Beschreibung (`--design`, z. B. „professionell, modern, minimalistisch,
Akzentfarbe Dunkelblau"). Dieses Feature ergänzt eine optionale, standardmäßig
**deaktivierte** CLI-Option `--match-style`, die stattdessen Stil-Signale der
Zielseite (der bereits vorhandenen `--target`-URL der Stellenanzeige)
ausliest — Akzentfarbe und Schriftcharakter (serif/sans-serif) — und diese als
verbindliche Design-Vorgabe an CV **und** Anschreiben durchreicht.

Ziel ist, dass generierte Bewerbungsunterlagen optisch an die Marke des
potenziellen Arbeitgebers angelehnt sind (Farbcodierung von Überschriften,
Fließtext, Akzenten), ohne dass der Nutzer die Farbe/Schriftart manuell in
`--design` nachpflegen muss.

`--match-style` setzt `--target` voraus. Ist keine `--target`-URL angegeben,
wird das Flag ignoriert (mit Hinweis in der Konsolenausgabe) und normal ohne
Style-Matching generiert — kein Fehlerabbruch.

Es wird bewusst **keine** neue `--company-url`-Option eingeführt: viele
Stellenanzeigen (auch auf Jobboards wie StepStone/LinkedIn) tragen zumindest
ein Mindestmaß an Corporate-Styling im Kopf-/Fußbereich; eine zweite,
optionale URL-Option hätte die CLI-Oberfläche unnötig vergrößert. Ebenso wird
bewusst **kein** Screenshot-/Vision-Ansatz verfolgt (kein Playwright o. Ä. als
neue Abhängigkeit) — stattdessen eine leichtgewichtige HTML/CSS-Text-Heuristik
auf Basis der bereits vorhandenen `requests`+`BeautifulSoup`-Infrastruktur.

Granularität bewusst minimal gehalten: **eine** Akzentfarbe + **eine**
Schriftart (kein separates Rollensystem für Überschrift-/Fließtext-Farbe oder
-Schrift) — das entspricht dem bestehenden Ein-Farbe/Ein-Font-Modell der
Typst-/HTML-Templates und braucht daher keine strukturelle Änderung an deren
Layout-Logik.

Der bestehende CV→Anschreiben-Konsistenzmechanismus
(`_extract_design_tokens()` in `core/agent.py`, der nach der CV-Generierung
Akzentfarbe/Schriftart aus dem erzeugten Dokument ausliest und dem
Anschreiben-Agenten als bindende Vorgabe mitgibt) bleibt die Quelle der
Wahrheit für den *innerhalb eines Laufs* tatsächlich gerenderten Wert. Die aus
`--match-style` gewonnenen Marken-Tokens sind der **Ausgangswert**, den der
CV-Agent verbindlich übernehmen soll; das Anschreiben übernimmt danach wie
gehabt, was tatsächlich im CV gelandet ist (Fallback auf die Marken-Tokens,
falls die Regex-Extraktion aus dem generierten CV nichts findet, z. B. weil
kein CV in diesem Lauf erzeugt wurde).

## Voraussetzungen

- **Neuer Agent-Prompt für Stilanalyse**: analog zu `agents/job-analyzer.md`
  braucht es `agents/style-analyzer.md` — nimmt eine vorverarbeitete Liste von
  Hex-/RGB-Farben und `font-family`-Deklarationen (mit Häufigkeit) entgegen
  und leitet daraus eine plausible Markenfarbe sowie eine grobe
  Font-Klassifikation (`serif`/`sans-serif`) ab. Muss explizit angewiesen
  werden, UI-Neutralfarben (Grau/Schwarz/Weiß) und einmalige Ausreißer zu
  ignorieren und bei Unsicherheit `null` statt zu raten zurückzugeben.
- **`core/scraper.py`** hat aktuell nur `fetch_job_posting()`, das über
  `_NOISE_TAGS` gezielt `<style>`-Tags entfernt und daher für Stilextraktion
  ungeeignet ist. Es braucht eine zweite, unabhängige Fetch-Funktion, die
  `<style>`-Blöcke, verlinkte Stylesheets und das `theme-color`-Meta-Tag
  gezielt einsammelt statt sie zu verwerfen.
- **`core/agent.py`**: `generate_cv()` akzeptiert bisher keinen
  `design_tokens`-Parameter — dieser Mechanismus existiert nur bei
  `generate_cover_letter()`. Muss symmetrisch ergänzt werden, sonst kann eine
  aus `--match-style` gewonnene Markenfarbe nicht in den CV einfließen. Die
  "Verwende exakt: …"-Logik ist in `generate_cover_letter()` aktuell inline
  dupliziert und sollte beim Ergänzen in `generate_cv()` in einen
  gemeinsamen Helper gezogen werden statt ein zweites Mal kopiert zu werden.
- **`agents/cv-typst.md`/`agents/cv-html.md`** haben — anders als
  `cover-typst.md`/`cover-html.md` — noch keine bindende Regel „werden
  konkrete Design-Vorgaben mitgeliefert, sind exakt diese zu verwenden statt
  eigene zu wählen". Ohne diese Ergänzung würde der CV-Agent die per
  `--match-style` ermittelten Marken-Tokens ignorieren können.
- **Verfügbare Fonts sind pro Engine fest begrenzt** (Typst: „Liberation
  Sans", „Liberation Serif", „DejaVu Sans", „DejaVu Serif", „New Computer
  Modern"; HTML: Arial, Helvetica, Georgia, „Segoe UI", sans-serif, serif) —
  echte Markenschriften (z. B. „Circular", „Gotham") lassen sich nicht 1:1
  übernehmen. Die Stilanalyse liefert deshalb bewusst nur eine grobe
  Klassifikation (`serif`/`sans-serif`), die in Python deterministisch auf
  einen konkreten, bereits als sicher dokumentierten Font gemappt wird —
  keine Freitext-Fontnamen von Claude direkt übernehmen.

## Steps

1. `agents/style-analyzer.md` anlegen (Frontmatter `name`, `description`,
   `model: claude-opus-4-7` analog zu den bestehenden Agenten). Erwartet
   einen Text-Digest aus gezählten Farben/Font-Deklarationen, antwortet
   ausschließlich mit
   `{"primary_color": "#RRGGBB" | null, "font_style": "serif" | "sans-serif" | null}`.
2. `core/scraper.py`: `fetch_style_signals(url, timeout=15, max_stylesheets=3) -> Optional[str]`
   ergänzen — GET auf `url` mit den bestehenden `_HEADERS`, `theme-color`-Meta
   auslesen, alle Inline-`<style>`-Blöcke sammeln, bis zu 3 verlinkte
   Stylesheets nachladen (relative URLs via `urljoin` auflösen, je ~50 KB
   gedeckelt, einzelne Fehler pro Stylesheet überspringen statt
   abzubrechen). Aus dem kombinierten CSS-Text per Regex Hex-/RGB-Farben und
   `font-family`-Werte extrahieren, mit `collections.Counter` nach Häufigkeit
   zählen und als kompakten Text-Digest zurückgeben (kein Roh-CSS an Claude
   schicken). `None` falls Seite nicht abrufbar oder nichts gefunden wurde.
3. `core/agent.py`:
   - `_style_meta, _STYLE_ANALYSIS_PROMPT = _load_agent("style-analyzer.md")`
     beim Modul-Import laden.
   - `analyze_style(client, style_signals: str) -> Optional[dict]` ergänzen,
     analog zu `analyze_job_posting()` (niedriges `max_tokens`, z. B. 256,
     da nur ein kleines JSON-Objekt erwartet wird).
   - `_SAFE_FONTS = {"typst": {"sans-serif": "Liberation Sans", "serif": "Liberation Serif"}, "html": {"sans-serif": "Arial", "serif": "Georgia"}}`
     ergänzen.
   - `resolve_brand_tokens(style_analysis: Optional[dict], engine: str) -> Optional[dict]`
     ergänzen — baut daraus `{"accent": ..., "font": ...}` (gleiche Form wie
     die `_extract_design_tokens()`-Rückgabe), `None` falls nichts
     Verwertbares dabei ist.
   - Gemeinsamen Helper `_apply_design_tokens(design_block: str, design_tokens: Optional[dict]) -> str`
     ergänzen (aktuell inline in `generate_cover_letter()` dupliziert) und
     von dort **und** von `generate_cv()` verwenden.
   - `generate_cv(...)` um `design_tokens: Optional[dict] = None` erweitern
     und über `_apply_design_tokens()` auf den `design_block` anwenden.
4. `agents/cv-typst.md` und `agents/cv-html.md`: dieselbe bindende Regel
   ergänzen, die `cover-typst.md`/`cover-html.md` bereits haben — „Werden
   konkrete Design-Vorgaben (Akzentfarbe, Schriftart) im User-Prompt
   mitgeliefert, sind exakt diese Werte zu verwenden statt eigene zu wählen."
5. `generate.py`:
   - Neues Argument `--match-style` (`action="store_true"`, Standard aus)
     ergänzen, Docstring-Beispiel und Hilfetext ergänzen.
   - Imports erweitern: `fetch_style_signals` aus `core.scraper`,
     `analyze_style`, `resolve_brand_tokens` aus `core.agent`.
   - Vor der CV/Anschreiben-Generierung (nach `ts = new_timestamp()`):
     `design_tokens` aus Markenanalyse berechnen, falls `--match-style`
     gesetzt ist — ohne `--target` nur Hinweis ausgeben und ohne
     Style-Matching weiterlaufen; bei nicht abrufbarer Seite oder
     uneindeutigem Ergebnis ebenfalls sauber auf „ohne Style-Matching"
     zurückfallen statt abzubrechen.
   - `generate_cv(...)`-Aufruf um `design_tokens=design_tokens` erweitern.
   - Bestehende Zeile `design_tokens = _extract_design_tokens(cv_source, args.engine)`
     (nur im `if want_cv: ... if want_cover:`-Zweig) zu
     `design_tokens = _extract_design_tokens(cv_source, args.engine) or design_tokens`
     ändern — Rückfall auf die Marken-Tokens, falls die Regex-Extraktion aus
     dem generierten CV nichts liefert. Dadurch greift Style-Matching auch
     bei reinen `--cover`-Läufen (kein CV in diesem Lauf, `design_tokens`
     bleibt dann direkt der Marken-Wert).
6. `README.md`: `--match-style`-Beispiel im Usage-Block ergänzen (Hinweis:
   erfordert `--target`).
7. `CLAUDE.md` aktualisieren: kurzer Hinweis im Abschnitt
   „Generierungsablauf", dass optional per `--match-style` Akzentfarbe/
   Schriftart der Zielseite übernommen werden können.
8. Manuell testen (kein bestehendes Testsetup im Projekt, konsistent damit
   per CLI verifizieren):
   - `--match-style --target <echte Firmen-Stellenanzeige-URL>` — Konsolen-
     ausgabe prüfen, erzeugtes `.typ`/`.html` auf die erwartete Akzentfarbe/
     Schriftart prüfen.
   - `--match-style` ohne `--target` — Skip-Meldung, kein Crash.
   - `--match-style --target <URL ohne erkennbares Branding>` — sauberer
     Rückfall auf „kein eindeutiger Markenstil" statt Raten.
   - `--cover --match-style --target <URL>` ohne `--cv` — Anschreiben nutzt
     die Marken-Tokens direkt, ohne dass vorher ein CV erzeugt wurde.
   - Jeweils für `--engine typst` und `--engine html` durchspielen.
