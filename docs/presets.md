# Presets

| Preset | Kind | Notes |
|---|---|---|
| `nature` | journal | 89 / 183 mm, ≤170 mm high, 5–7 pt sans-serif, 8 pt bold panel labels ([source](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications)) |
| `bbc` | news | BBC [bbplot](https://github.com/bbc/bbplot) style: 640×450 px, Helvetica 28/22/18 pt |
| `nyt-like`, `wapo-like`, `ft-like`, `economist-like` | news | Inspired by public chart conventions; not affiliated with the publishers |
| `screen`, `web`, `a4`, `letter`, `poster`, `slide-16x9` | generic | Everyday output sizes |

Add your own with `sp.presets.register("my_lab.toml")`. See `CONTRIBUTING.md`
for the file format.
