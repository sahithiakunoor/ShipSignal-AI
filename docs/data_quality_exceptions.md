# Milestone 1 data-quality exception

## DQ-001: supplied category translation lookup is incomplete

**Disposition:** Documented exception for the reviewed local snapshot. The measured check remains failed. No automatic waiver or validation-code change has been made.

**Evidence provenance:** The project owner supplied the generated source dictionary, ingestion output and failed-check JSON in this conversation. This records that evidence; it is not an independent cloud rerun. Loaded schema: `raw_dbfbd3a2636389441845`. Full snapshot identity, file checksums and timestamps remain in the owner's local manifest.

| Check field | Observed value |
|---|---:|
| Check | `products.product_category_name.relationship` |
| Nonblank product rows with an unmatched category | 13 |
| Products with a missing category | 610 |
| Missing parent category keys | 0 |
| Excess duplicate parent category keys | 0 |

The owner separately listed the unmatched values directly from the unchanged CSVs:

| Original category | Product rows |
|---|---:|
| `pc_gamer` | 3 |
| `portateis_cozinha_e_preparadores_de_alimentos` | 10 |

These are 13 product records across two distinct unmatched categories, not 13 categories. Missing categories are permitted by this relationship's `nullable=True`; the 610 missing values are profiled but are not its failure trigger. Nonblank unmatched values still fail referential coverage.

## Handling decision and rationale

Retain every product and its original category. Leave the supplied English translation unavailable for an unmatched category. Never invent translations or silently delete rows to pass a gate. A later typed layer should distinguish missing source category from present-but-unmapped category. Future translation enrichment must use LEFT JOIN, with parent category uniqueness checked first, to preserve products and avoid duplication. That enrichment is a requirement, not an implementation in this milestone.

The alternative is to reject ingestion until the public lookup is complete. That would prevent an otherwise faithful raw load for an optional enrichment field. Preserving and explicitly documenting the gap supports truthful analysis without claiming perfect quality.

## Operational behavior

- Source validation: **34/35 passed**, as reported by the owner.
- Full validation: **56/57 passed**, with this sole failed check, as reported by the owner.
- Of those checks, **22/22 database reconciliation checks passed** (57 total minus 35 source checks). These verify raw row counts, ordered parsed-field content, independent monetary sums and aggregate-join conservation.
- Overall JSON `passed` remains `false`; `shipsignal validate` continues to exit with status **1** for this snapshot. Exit status **2** means an operational error, not this documented finding.
- Descriptive acceptance is **complete with one documented exception**, not “all checks passed.” No warning framework, allowlist, category repair or hard-coded pass count is implemented.

Reinspect when source bytes change. Do not automatically extend this exception to new unmatched categories, different counts, missing/nonunique parent keys, or unrelated order relationships. Compare the next report with this evidence and investigate differences.
