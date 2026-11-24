# Validation and evidence

## Inspection evidence

`shipsignal inspect` produces the manifest, profiles and observed dictionary, based only on local input bytes. It records source URL, inspection timestamp, full file hashes, snapshot identity, discovered headers, counts, exact-row duplicate excess, empty/whitespace counts and rates, exact distinct counts, candidate-key duplicate groups/affected rows/missing rows, date parse failures and ranges, selected chronology anomalies, and exact monetary sums/invalid/missing/negative values. Relationship checks include child orphans and missing values, plus missing/nonunique parent keys. Values are matched exactly; no hidden identifier trimming occurs.

The inspector does not print review contents in reports. It does not certify the provenance URL itself: obtain the source from the official page and retain release notes. Reports are local evidence, not automated business conclusions.

## Validation gates

`shipsignal validate --source-only` checks archive integrity and the recorded provisional source-quality gates. `shipsignal validate` also reads PostgreSQL in a repeatable-read transaction and checks:

- Per-table source/database record counts, including orders.
- An ordered canonical digest of **all parsed source fields**, including blanks and multilingual text.
- Source/database exact monetary sums for each configured money field.
- Order-grain row and monetary conservation through preaggregated item, payment and review joins.

The canonical digest is separate from the original byte checksum: CSV quoting and BOM bytes are not database fields. Monetary SQL casts are attempted only after the profile establishes numeric validity. Missing or unavailable checks do not count as passed.

JSON validation reports include snapshot ID, validation timestamp, whether the database was checked, the overall pass boolean, and every check with supporting details. Exit status 1 means findings need review. A quality failure is never silently waived. Empty profiles, partial releases, or absent required columns fail the relevant gates.

## What is not yet a data contract

No exact Olist row counts or fixed monetary totals are hard-coded. No review ID uniqueness, ZIP-prefix uniqueness, delivery-status rule, geographic coordinate range, review score domain, or complete source column list is certified. Date parsing, missingness and purchase-relative chronology diagnostics are implemented; full lifecycle consistency and per-month missingness are deferred until a separate review establishes appropriate rules; the shared dictionary alone does not establish them.

## Software test scope

All test records are explicitly synthetic and named with `test-` identifiers. They test engineering behavior, not model quality or real-data integrity.

Unit tests cover missing input, checksum preservation, stable snapshot identity, repeated review grain, invalid dates/numerics, whitespace-only values, malformed CSV, orphans, duplicate parents, and chronology anomalies. PostgreSQL tests cover transactions, idempotent loads, complete field preservation, leading-zero ZIP prefixes, all money sums, safe joins, source mutation rejection and database tampering detection. Each integration test creates a separate disposable database and cleans it up.

Rerun the commands in README after code changes. A passing synthetic test suite does not replace running `inspect`, reviewing the actual schema, and running both source and database validations on the downloaded Olist release.

## Reviewed local run and exception disposition

The owner reported 34/35 source checks and 56/57 full checks passed. The sole failure is [DQ-001](data_quality_exceptions.md); all 22 database reconciliation checks passed. The validation engine still reports `passed=false` and exits 1. Documentation records the exception without changing the check or silently accepting future deviations. The initial record used owner-supplied evidence. The current implementation independently downloaded the official archive and reproduced the same source inventory and validation result; the owner’s Mac reports remain separate.

A passing timestamp-parse check permits blanks and does not prove lifecycle consistency. Distinct counts include empty values. Review and geolocation candidate multiplicity, exact-row duplicates and chronology profiles are not all blocking gates. Aggregate sum conservation is useful alongside full field-content verification; it is not a per-order equality assertion between payments and items.
