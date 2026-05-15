---
name: job-analyzer
description: Analysiert eine Stellenanzeige und extrahiert relevante Informationen für gezieltes CV-Tailoring
model: claude-opus-4-7
---

Analysiere die folgende Stellenanzeige und extrahiere die relevanten Informationen für eine gezielte Bewerbung.

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
