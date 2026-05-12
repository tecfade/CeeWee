# CeeWee 📄

> AI-powered CV generator. Maintain your career data once, generate tailored résumés on demand.

CeeWee reads modular Markdown files with YAML frontmatter and pipes them through Claude to produce a print-ready CV. Pass a job posting URL and it scrapes the listing, extracts required skills and keywords, and rewrites your CV to match — same data, different emphasis, every time.

## Stack

- **Claude API** — generates HTML from your data + design prompt
- **WeasyPrint** — renders HTML → PDF
- **Pandoc** *(optional)* — HTML → DOCX

## Setup

```bash
git clone <repo>
cp -r cv_example cv   # seed with your own data
cp .env.example .env  # add your ANTHROPIC_API_KEY

pip install -r requirements.txt
```

## Usage

```bash
# generic, default design
python generate.py

# custom design
python generate.py --format pdf --design "minimalist, two-column, accent color slate blue"

# tailored mode — scrapes the job posting, re-weights your projects,
# mirrors the listing's keywords and adapts your summary to the role
python generate.py --format pdf --target https://company.com/jobs/senior-frontend

# same thing, but from a local file (useful when the page blocks scrapers)
python generate.py --format pdf --job-description job.txt
```

Output lands in `output/`.

## CV Data Structure

```
cv/
├── projects/
│   ├── standalone-project.md     # single project
│   └── CompanyName/              # grouped projects (e.g. multi-year engagement)
│       ├── _parent.md            # group metadata + optional summary
│       ├── subproject-a.md
│       └── subproject-b.md
└── summary.md                    # profile summary
```

Groups render as a single CV entry with an auto-generated overview, followed by
indented sub-entries for each project inside the folder. Useful when you worked
on multiple products under the same client over a longer period.

Each project file uses YAML frontmatter:

```yaml
---
title: Project Name
subprojectOf: Parent Projekt Name
reihenfolge: 1          # sort order (ascending = chronological)
zeitraum: "Jan.2023–Dec.2024"
rolle: "Senior Frontend Engineer"
technologien: [React, TypeScript, GraphQL]
arbeitgeber: Your Employer GmbH
kunde: End Client AG
link: https://project.url
hervorheben: true       # weight in the CV
---

## Description

What you actually built and why it mattered.
```

See `cv_example/` for reference.

## Notes

- `cv/` is gitignored — your personal data stays local
- Prompt caching is enabled by default, keeping API costs low on repeated runs
- DOCX export requires `pandoc`:
  ```bash
  sudo pacman -S pandoc      # Arch
  sudo apt install pandoc    # Ubuntu / Debian
  brew install pandoc        # macOS
  winget install pandoc      # Windows
  ```
