# Trap verification

These checks were run on November 6, 2026 by `scripts/build_and_verify.py`. Each number
is computed from the saved GeoPackages, not from values held in memory. Full output:
`answer_keys/verification.json`.

## Does each trap give the wrong answer, and each clean version the right one?

| Task | Trap, done the obvious way | Trap, done correctly | Clean version |
|---|---|---|---|
| A. Density | 317 counties above 100/km², median 10.6 | 464, median 17.2 | 464, median 17.2 (planar area in EPSG:5070 is within 0.01% of geodesic) |
| B. Fast food | r = 0.64, slope 0.94 | Controlling for income: r = −0.05, slope −0.10, p = 0.66 | r = 0.57 raw, 0.69 controlling for income |
| C. Region error | Pooled slope +0.025 ("growth raises error") | Within-region slopes −0.036 and −0.054; region effect +0.28 | All slopes positive (+0.05); region effect −0.001, p = 0.91 |

## Is it the design or the seed?

Tasks B and C were regenerated with 500 other seeds. Share of seeds where the
property holds:

| Version | Property | Share |
|---|---|---|
| B trap | raw p < 0.01 and partial p > 0.05 | 93.2% |
| B clean | raw p < 0.01 and partial p < 0.01 | 97.0% |
| C trap | pooled slope > 0 (p < 0.01) and both within-region slopes < 0 | 99.8% |
| C clean | pooled and within-region slopes > 0, region effect p > 0.05 | 95.4% |

Task A has no randomness: Web Mercator inflates area by 1/cos²(latitude).

## Bugs caught while building

1. The first version of Task B used a log-scale income and an exponential fast-food
   rate. A straight-line income adjustment then left curvature behind, and the
   partial correlation came out at 0.59 instead of about 0. That would have penalised
   an agent for adjusting correctly. Fixed: all relationships are now linear in the
   observed income column.
2. numpy treats the seeds `[s, 2, 0]` and `[s, 2, 0, 0]` as the same. The trap's
   obesity noise therefore repeated the income draws exactly, and obesity came out
   constant. Fixed: every random stream now has a distinct, nonzero final tag.
