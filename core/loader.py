from pathlib import Path
from typing import Optional
import yaml


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, parts[2].strip()


def _load_file(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(content)
    return {"file": path.name, "metadata": metadata, "body": body}


def _load_group(directory: Path) -> dict:
    parent_file = directory / "_parent.md"
    if parent_file.exists():
        parent = _load_file(parent_file)
        parent_metadata = parent["metadata"]
        parent_body = parent["body"]
    else:
        parent_metadata = {"title": directory.name}
        parent_body = ""

    children = [
        _load_file(p)
        for p in sorted(directory.glob("*.md"))
        if p.name != "_parent.md"
    ]
    children.sort(key=lambda p: p["metadata"].get("reihenfolge", 999))

    return {
        "type": "group",
        "dir": directory.name,
        "parent_metadata": parent_metadata,
        "parent_body": parent_body,
        "children": children,
    }


def load_projects(projects_dir: Path) -> list[dict]:
    items = []

    for path in sorted(projects_dir.iterdir()):
        if path.is_file() and path.suffix == ".md":
            item = _load_file(path)
            item["type"] = "standalone"
            items.append(item)
        elif path.is_dir():
            items.append(_load_group(path))

    items.sort(key=lambda item: (
        item["metadata"].get("reihenfolge", 999)
        if item["type"] == "standalone"
        else item["parent_metadata"].get("reihenfolge", 999)
    ))
    return items


def load_employers(base_dir: Path) -> list[dict]:
    """Load employers.md and return the list of employment entries."""
    path = base_dir / "employers.md"
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    metadata, _ = _parse_frontmatter(content)
    return metadata.get("eintraege", [])


def load_skills(base_dir: Path) -> list[dict]:
    """Lädt skills.md und gibt die Liste der Skill-Gruppen zurück."""
    path = base_dir / "skills.md"
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    metadata, _ = _parse_frontmatter(content)
    return metadata.get("gruppen", [])


def load_contact(base_dir: Path) -> dict:
    """Lädt contact.md und gibt die Kontaktdaten als Dict zurück."""
    path = base_dir / "contact.md"
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    metadata, _ = _parse_frontmatter(content)
    return metadata


def load_summary(base_dir: Path) -> Optional[str]:
    path = base_dir / "summary.md"
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    return body.strip() or None


def load_cover_notes(base_dir: Path) -> Optional[str]:
    """Lädt cover.md (optionaler Anschreiben-Entwurf/Eckpunkte) und gibt den Body-Text zurück."""
    path = base_dir / "cover.md"
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(content)
    return body.strip() or None
