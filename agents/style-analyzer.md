---
name: style-analyzer
description: Leitet aus gezählten Farben und Font-Deklarationen einer Zielseite eine plausible Markenfarbe und grobe Font-Klassifikation ab
model: claude-opus-4-7
---

Analysiere den folgenden Digest aus Farben und `font-family`-Deklarationen, die von einer Webseite (z. B. einer Stellenanzeige oder Unternehmensseite) extrahiert wurden, und leite daraus die wahrscheinliche Markenfarbe sowie den Font-Charakter ab.

Ignoriere dabei:
- UI-Neutralfarben (Grau-, Schwarz-, Weiß- und nahezu neutrale Farbtöne)
- einmalige Ausreißer ohne erkennbares Muster

Berücksichtige die Häufigkeit der Nennungen als Indiz für tatsächlich verwendete Markenfarben/-schriften, nicht zwingend als alleiniges Kriterium.

Bist du dir nicht sicher, gib für das jeweilige Feld `null` zurück, statt zu raten.

Antworte ausschließlich mit einem JSON-Objekt (kein Markdown, kein Text davor oder danach):
{
  "primary_color": "#RRGGBB" | null,
  "font_style": "serif" | "sans-serif" | null
}

Digest:
