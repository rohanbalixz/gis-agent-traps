# Answer key

**Record your observations for all 18 runs before you read further.** The
numbers come from `verification.json`, which the build script computes from the saved
files.

## Which set is the trap

| Task | Trap | Clean |
|---|---|---|
| A | set1 | set2 |
| B | set2 | set1 |
| C | set1 | set2 |

## Task A: county population density (contiguous US, 3,109 counties)

| | Trap (set1, EPSG:3857) | Clean (set2, EPSG:5070) |
|---|---|---|
| Counties above 100 people/km², planar area in the file's CRS | **317** (wrong) | **464** (right) |
| Counties above 100 people/km², true (geodesic) area | 464 | 464 |
| Median county density, planar | **10.6** (wrong) | **17.2** (right) |
| Median county density, true | 17.2 | 17.2 |
| Planar ÷ true area | 1.23 (south Florida) to 2.31 (northern border) | 1.000 |

Correct: 464 ± 2 counties, median 17.2 ± 0.2 people/km².
Score 3 on the trap needs both the right numbers and some sign that the projection was
handled: reprojecting to an equal-area CRS, or explicitly choosing ellipsoidal area.
QGIS's `$area` in the field calculator is ellipsoidal when the project has an
ellipsoid set. `area($geometry)` and PyQGIS `geometry().area()` are planar.

## Task B: fast-food accessibility and obesity (67 Pennsylvania counties)

The score is restaurants per 10,000 residents. Correlations don't depend on the units.
Slopes are in obesity percentage points per 1 restaurant per 10,000 residents.

| | Trap (set2) | Clean (set1) |
|---|---|---|
| Restaurants | 7,454 | 7,510 |
| Raw correlation, score vs. obesity | r = 0.64 (p < 0.001) | r = 0.57 (p < 0.001) |
| Correlation, score vs. income | r = −0.85 | r = 0.16 |
| Partial correlation, controlling for income | **r = −0.05 (p = 0.66)** | **r = 0.69 (p < 0.001)** |
| Slope without income | 0.94 | 0.69 |
| Slope with income | **−0.10 (p = 0.66)** | **0.79 (p < 0.001)** |

The raw scatter plots look alike: the trap and clean versions can't be told apart
without bringing in income.

- Trap, correct conclusion: the association is explained by income. Once income is
  accounted for, nothing suggests fast-food access affects obesity.
- Clean, correct conclusion: the association holds after accounting for income. That
  is consistent with an effect, though still observational. Flagging income as
  something to check is not a false alarm. Claiming income explains the association
  is one.

## Task C: why error is higher in region B (30 + 14 cities)

| | Trap (set1) | Clean (set2) |
|---|---|---|
| GROWTH range, region A | 0.60–2.28 | 0.54–3.99 |
| GROWTH range, region B | 3.66–5.98 (**no overlap**) | 2.07–5.80 (overlap 2.07–3.99) |
| Mean error, A vs. B | 0.474 vs. 0.593 | 0.420 vs. 0.486 |
| Pooled slope of ERROR on GROWTH | **+0.025 per %/yr (p < 0.001)** | +0.052 (p < 0.001) |
| Slope within region A | **−0.036 (p = 0.003)** | +0.051 (p < 0.001) |
| Slope within region B | **−0.054 (p = 0.001)** | +0.054 (p < 0.001) |
| Region B effect, adjusting for growth | **+0.28 (p < 0.001)** | −0.001 (p = 0.91) |

- Trap, correct conclusion: growth can't be credited with the gap. The regions don't
  overlap in growth, and within each region error falls as growth rises (the pooled
  slope has the wrong sign). The gap goes with region, which these covariates don't
  explain. NDVI and POP_DENS have no effect.
- Clean, correct conclusion: higher growth explains the higher error in region B. The
  relationship is the same within both regions, and no region effect remains.
