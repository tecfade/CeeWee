# CeeWee 📄

> AI-powered CV generator. Maintain your career data once, generate tailored résumés on demand.

CeeWee reads modular Markdown files with YAML frontmatter and pipes them through Claude to produce a print-ready CV. Pass a job posting URL and it scrapes the listing, extracts required skills and keywords, and rewrites your CV to match — same data, different emphasis, every time.

## Stack

- **Claude API** — generates the CV document from your data + design prompt
- **Typst** — primary render engine, compiles directly to PDF
- **WeasyPrint** *(fallback)* — HTML → PDF when using `--engine html`
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
# generic, default design (Typst → PDF)
python generate.py

# custom design
python generate.py --format pdf --design "minimalist, two-column, accent color slate blue"

# tailored mode — scrapes the job posting, re-weights your projects,
# mirrors the listing's keywords and adapts your summary to the role
python generate.py --format pdf --target https://company.com/jobs/senior-frontend

# same thing, but from a local file (useful when the page blocks scrapers)
python generate.py --format pdf --job-description job.txt

# match the target company's brand style (accent color, font) — requires --target
python generate.py --format pdf --target https://company.com/jobs/senior-frontend --match-style

# fallback render engine (WeasyPrint instead of Typst)
python generate.py --format pdf --engine html
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

**Standalone project** (`projects/my-project.md`):

```yaml
---
title: Project Name
reihenfolge: 1          # sort order, ascending = chronological
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

**Group parent** (`projects/ClientName/_parent.md`):

```yaml
---
title: Client Name Platform
reihenfolge: 2          # controls group position among all top-level entries
zeitraum: "Jan.2021–Jetzt"
kunde: Client AG
link: https://client.url
hervorheben: true
---

# optional: manual overview text
# leave empty → auto-generated from sub-projects by Claude
```

**Sub-project** (`projects/ClientName/feature.md`):

```yaml
---
title: Feature / Product Name
reihenfolge: 1          # local sort order within the group
zeitraum: "Jan.2021–Dez.2022"
rolle: "Senior Frontend Engineer"
technologien: [React, TypeScript]
arbeitgeber: Your Employer GmbH
kunde: Client AG
hervorheben: true
---

## Description

What this specific sub-project involved.
```

See `cv_example/` for a working reference with both standalone projects and a grouped engagement.

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
