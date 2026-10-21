# Presets

| Preset | Kind | Notes |
|---|---|---|
| `nature` | journal | 89 / 183 mm, ≤170 mm high, 5–7 pt sans-serif, 8 pt bold panel labels ([source](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications)) |
| `science` | journal | 90 / 183 mm, 6–9 pt Arial/Helvetica, lines ≥0.28 pt, 10 pt bold panel labels ([source](https://www.science.org/cms/asset/62583409-a188-466e-8cc0-6fb5f083bbff/author_prep_guide_2025.pdf)) |
| `cell` | journal | 85 / 114 / 174 mm, 6–8 pt Arial, lines ≥0.5 pt, capital panel labels ([source](https://www.cell.com/figureguidelines)) |
| `pnas` | journal | 87 / 114 / 178 mm, ≤225 mm high, text ≥6 pt, lines ≥0.25 pt ([source](https://www.pnas.org/pb-assets/authors/digitalart-1675347574760.pdf)) |
| `aha` | journal | AHA journals (Circulation, Hypertension, …): 80 / 127.5 / 177.5 mm, 6–10 pt Arial, 12.6 pt bold panel labels ([source](https://www.ahajournals.org/pb-assets/migration/Hype_InstructionsforFigureSubmission.pdf)) |
| `ieee` | journal | 3.5 / 7.16 in, ≤8.8 in high, ~9–10 pt Helvetica/Arial ([source](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/improve-your-graphics/)) |
| `acm` | journal | acmart `sigconf` column / text width (240 / 504 pt), 8–9 pt text ([source](https://github.com/borisveytsman/acmart/blob/master/acmart.dtx)) |
| `elsevier` | journal | 30 / 90 / 140 / 190 mm, ~7 pt text, ≥6 pt ([source](https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-sizing)) |
| `springer` | journal | 84 / 174 mm (`small` = 119 mm), ≤234 mm high, 8–12 pt Helvetica/Arial, lines ≥0.3 pt ([source](https://link.springer.com/journal/11145/submission-guidelines)) |
| `neurips` | journal | 5.5 in text width, 8–10 pt text ([source](https://media.neurips.cc/Conferences/NeurIPS2025/Styles.zip)) |
| `bbc` | news | BBC [bbplot](https://github.com/bbc/bbplot) style: 640×450 px, Helvetica 28/22/18 pt |
| `nyt-like`, `wapo-like`, `ft-like`, `economist-like` | news | Inspired by public chart conventions; not affiliated with the publishers |
| `screen`, `web`, `a4`, `letter`, `poster`, `slide-16x9` | generic | Everyday output sizes |

Add your own with `sp.presets.register("my_lab.toml")`. See `CONTRIBUTING.md`
for the file format.
