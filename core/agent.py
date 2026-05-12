import json
import os
from typing import Optional

import anthropic

MODEL = "claude-sonnet-4-6"

# ── System prompts ────────────────────────────────────────────────────────────

_TYPST_SYSTEM_PROMPT = """\
Du bist ein professioneller Lebenslauf-Assistent für deutschsprachige Bewerbungen im IT-Bereich.

Deine Aufgabe: Aus strukturierten Projektdaten einen vollständigen, druckfertigen Lebenslauf \
als Typst-Dokument generieren.

## Typst-Syntax (Kurzreferenz)

```
#set page(paper: "a4", margin: (x: 1.5cm, y: 2cm))
#set text(font: "Liberation Sans", size: 10pt, lang: "de")
#set par(leading: 0.6em)

#let accent = rgb("#1565C0")          // Farbe definieren

#text(weight: "bold")[Fett]           // Fettschrift
#text(fill: accent)[Farbig]           // Farbe
#align(center)[Zentriert]             // Ausrichtung
#line(length: 100%, stroke: 0.5pt)    // Trennlinie
#v(0.5em)                             // Vertikaler Abstand
#h(1fr)                               // Flexibler horizontaler Abstand
#grid(columns: (1fr, auto), [...], [...])  // Zweispaltiges Layout
```

Verfügbare Fonts (sicher auf Linux): "Liberation Sans", "Liberation Serif", \
"DejaVu Sans", "DejaVu Serif", "New Computer Modern"

Nicht existierende Funktionen — verwende diese NICHT: `#wrap-content`, `#layout`, `#place`

## CV-Aufbau

1. Header — Name prominent, Kontaktdaten klein darunter
2. Profil/Summary — kompakte Zusammenfassung
3. Berufserfahrung — Projekte neueste zuerst (absteigende reihenfolge)
   - Standalone-Projekte: Titel + Zeitraum, Arbeitgeber/Kunde, Tech-Tags, Beschreibungspunkte
   - Gruppen (erkennbar an `[GRUPPE]`): Übergeordneter Eintrag mit Gesamtzeitraum und \
kurzem Überblick (max. 2 Sätze), darunter die Unterprojekte als eingerückte Unterabschnitte. \
Hat die Gruppe keinen eigenen Beschreibungstext, generiere den Überblick aus den Unterprojekten.
4. Skills — alle Technologien kategorisiert (Frontend, Backend, Testing, Tools, CI/CD)

## Ausgaberegeln — bindend

- Ausgabe: **ausschließlich** valides Typst-Markup — kein Text davor oder danach
- Keine Code-Fences (kein ```typst Block)
- Platzhalter `[TODO: ...]`, `[Zeitraum prüfen]`, `[Startdatum ergänzen]`, \
`[Zeitraum unbekannt]` erscheinen **nicht** im Output
- `ca. Aug.2025–Nov.2025` direkt ausgeben, ohne Marker
- Sprache: durchgehend Deutsch
- Kompakt: Ziel sind 1–2 DIN-A4-Seiten
- Keine externen Ressourcen oder URLs im Typst-Code
"""

_HTML_SYSTEM_PROMPT = """\
Du bist ein professioneller Lebenslauf-Assistent für deutschsprachige Bewerbungen im IT-Bereich.

Deine Aufgabe: Aus strukturierten Projektdaten einen vollständigen, druckfertigen Lebenslauf \
als HTML-Dokument generieren.

## CV-Aufbau

1. Header — Name, ggf. Kontaktdaten
2. Profil/Summary — kompakte Zusammenfassung (3–5 Sätze)
3. Berufserfahrung — Projekte neueste zuerst (absteigende reihenfolge)
4. Skills — alle Technologien aus allen Projekten, sinnvoll kategorisiert

## Ausgaberegeln — bindend

- Ausgabe: **ausschließlich** ein vollständiges HTML5-Dokument von `<!DOCTYPE html>` bis `</html>`
- CSS vollständig inline im `<style>`-Block — keine externen Stylesheets, kein JavaScript
- Nur systemnahe Schriften: Arial, Helvetica, Georgia, "Segoe UI", sans-serif, serif
- Platzhalter `[TODO: ...]`, `[Zeitraum prüfen]`, `[Startdatum ergänzen]`, \
`[Zeitraum unbekannt]` erscheinen **nicht** im Output
- Sprache: durchgehend Deutsch
- Print-optimiert: `@media print`, DIN-A4 (210mm × 297mm), Ziel 1–2 Seiten
"""

_JOB_ANALYSIS_PROMPT = """\
Analysiere die folgende Stellenanzeige und extrahiere die relevanten Informationen \
für eine gezielte Bewerbung.

Antworte ausschließlich mit einem JSON-Objekt (kein Markdown, kein Text davor oder danach):
{
  "position": "Jobtitel",
  "unternehmen": "Unternehmensname",
  "technologien": ["Tech1", "Tech2"],
  "keywords": ["Keyword1", "Keyword2"],
  "schwerpunkte": ["Schwerpunkt1"],
  "kultur": "Kurze Beschreibung der Unternehmenskultur",
  "erfahrungslevel": "Junior|Mid|Senior"
}

Stellenanzeige:
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def analyze_job_posting(client: anthropic.Anthropic, job_text: str) -> Optional[dict]:
    """Extract structured requirements from a raw job posting text."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": _JOB_ANALYSIS_PROMPT + job_text[:8000]}],
    )
    try:
        return json.loads(response.content[0].text)
    except (json.JSONDecodeError, IndexError, KeyError):
        return None


def _format_project(p: dict, heading: str = "###") -> str:
    m = p["metadata"]
    lines = [f"{heading} {m.get('title', p['file'])}"]
    for key in ("reihenfolge", "zeitraum", "rolle", "arbeitgeber", "kunde",
                "technologien", "link", "hervorheben"):
        val = m.get(key)
        if val is not None:
            lines.append(f"- **{key}**: {val}")
    if p["body"]:
        lines.append("")
        lines.append(p["body"])
    return "\n".join(lines)


def _format_group(group: dict) -> str:
    pm = group["parent_metadata"]
    lines = [f"### {pm.get('title', group['dir'])} [GRUPPE]"]
    for key in ("reihenfolge", "zeitraum", "arbeitgeber", "kunde", "hervorheben"):
        val = pm.get(key)
        if val is not None:
            lines.append(f"- **{key}**: {val}")
    if group["parent_body"]:
        lines.append("")
        lines.append(group["parent_body"])
    else:
        lines.append("")
        lines.append("_(Überblick aus Unterprojekten generieren)_")
    lines.append("")
    lines.append("#### Unterprojekte:")
    for child in group["children"]:
        lines.append("")
        lines.append(_format_project(child, heading="#####"))
    return "\n".join(lines)


def _build_project_data(projects: list[dict], summary: Optional[str]) -> str:
    parts = []

    if summary:
        parts.append(f"## Kandidaten-Profil\n\n{summary}")

    parts.append("## Projekte")
    for item in projects:
        if item["type"] == "standalone":
            parts.append(_format_project(item))
        else:
            parts.append(_format_group(item))

    return "\n\n".join(parts)


def _build_tailoring_block(job: dict) -> str:
    techs = ", ".join(job.get("technologien", []))
    keywords = ", ".join(job.get("keywords", []))
    schwerpunkte = ", ".join(job.get("schwerpunkte", []))
    return f"""\
## Tailoring für diese Stelle

Position: {job.get('position', '–')} bei {job.get('unternehmen', '–')}
Erfahrungslevel: {job.get('erfahrungslevel', '–')}
Gesuchte Technologien: {techs}
Wichtige Keywords: {keywords}
Schwerpunkte: {schwerpunkte}
Unternehmenskultur: {job.get('kultur', '–')}

Tailoring-Anweisungen:
- Passe den Summary-Text auf Position und Unternehmen an
- Hebe Projekte hervor, die die gesuchten Technologien enthalten
- Verwende die genannten Keywords natürlich in den Beschreibungen
- Priorisiere Erfahrungen, die zu den Schwerpunkten passen
- Behalte die umgekehrte chronologische Reihenfolge bei\
"""


# ── Public API ────────────────────────────────────────────────────────────────

def generate_cv(
    projects: list[dict],
    summary: Optional[str],
    design_prompt: str,
    engine: str = "typst",
    job_analysis: Optional[dict] = None,
    api_key: Optional[str] = None,
) -> str:
    """Call Claude API and return a CV document (Typst or HTML depending on engine)."""
    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    system_prompt = _TYPST_SYSTEM_PROMPT if engine == "typst" else _HTML_SYSTEM_PROMPT
    project_data = _build_project_data(projects, summary)
    design_block = f"## Design-Anforderungen\n\n{design_prompt}"

    user_message_parts = [
        {
            "type": "text",
            "text": project_data,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "\n\n---\n\n".join(
                [design_block] + ([_build_tailoring_block(job_analysis)] if job_analysis else [])
            ),
        },
    ]

    response = client.messages.create(
        model=MODEL,
        max_tokens=8096,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message_parts}],
    )

    return response.content[0].text
