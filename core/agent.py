import json
import os
from pathlib import Path
from typing import Optional

import anthropic
import yaml

AGENTS_DIR = Path(__file__).parent.parent / "agents"


# ── Agent file loader ─────────────────────────────────────────────────────────

def _load_agent(filename: str) -> tuple[dict, str]:
    """Parse an agent .md file and return (frontmatter, body)."""
    content = (AGENTS_DIR / filename).read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    meta = yaml.safe_load(parts[1]) or {}
    return meta, parts[2].strip()


# Load agents at import time
_typst_meta, _TYPST_SYSTEM_PROMPT = _load_agent("cv-typst.md")
_html_meta, _HTML_SYSTEM_PROMPT = _load_agent("cv-html.md")
_analyzer_meta, _JOB_ANALYSIS_PROMPT = _load_agent("job-analyzer.md")

MODEL = _typst_meta.get("model", "claude-opus-4-7")


# ── Helpers ───────────────────────────────────────────────────────────────────

def analyze_job_posting(client: anthropic.Anthropic, job_text: str) -> Optional[dict]:
    """Extract structured requirements from a raw job posting text."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": _JOB_ANALYSIS_PROMPT + "\n\n" + job_text[:8000]}],
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


def _build_skills_block(gruppen: list[dict]) -> str:
    lines = ["## Skills"]
    for gruppe in gruppen:
        name = gruppe.get("name", "")
        skills = gruppe.get("skills", [])
        if isinstance(skills, list):
            skills_str = ", ".join(str(s) for s in skills)
        else:
            skills_str = str(skills)
        lines.append(f"- **{name}**: {skills_str}")
    return "\n".join(lines)


def _build_employers_block(employers: list[dict]) -> str:
    lines = ["## Beruflicher Werdegang"]
    for e in employers:
        zeitraum = e.get("zeitraum", "")
        arbeitgeber = e.get("arbeitgeber", "")
        rolle = e.get("rolle", "")
        lines.append(f"- **{zeitraum}** — {arbeitgeber} | {rolle}")
    return "\n".join(lines)


def _build_project_data(
    projects: list[dict],
    summary: Optional[str],
    hobby_projects: Optional[list[dict]] = None,
    employers: Optional[list[dict]] = None,
    skills: Optional[list[dict]] = None,
) -> str:
    parts = []

    if summary:
        parts.append(f"## Kandidaten-Profil\n\n{summary}")

    if employers:
        parts.append(_build_employers_block(employers))

    if skills:
        parts.append(_build_skills_block(skills))

    parts.append("## Projekte")
    for item in projects:
        if item["type"] == "standalone":
            parts.append(_format_project(item))
        else:
            parts.append(_format_group(item))

    if hobby_projects:
        parts.append("## Eigene Projekte")
        for item in hobby_projects:
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
    hobby_projects: Optional[list[dict]] = None,
    employers: Optional[list[dict]] = None,
    skills: Optional[list[dict]] = None,
    job_analysis: Optional[dict] = None,
    api_key: Optional[str] = None,
) -> str:
    """Call Claude API and return a CV document (Typst or HTML depending on engine)."""
    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    system_prompt = _TYPST_SYSTEM_PROMPT if engine == "typst" else _HTML_SYSTEM_PROMPT
    project_data = _build_project_data(projects, summary, hobby_projects, employers, skills)
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
