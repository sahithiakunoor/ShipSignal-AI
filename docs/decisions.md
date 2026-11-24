# Decisions, alternatives, and assumptions

## Raw representation

**Chosen:** original-file checksum archive plus source-shaped PostgreSQL text tables.

Typed staging would make SQL easier immediately, but malformed timestamps, blanks, ZIP prefixes, and duplicate business keys could be rejected or changed before inspection. JSONB-only ingestion would tolerate arbitrary fields but make source-shaped SQL less approachable. Text columns retain explainability and allow later typed core transforms after evidence review. The CSV bytes, not the database field representation, are the byte-preservation authority.

## Load strategy

**Chosen:** one transaction per dataset snapshot, PostgreSQL COPY, new schema per changed snapshot, no automatic upserts.

Truncate/reload is simpler but destroys the prior load. Row upserts need verified business keys, especially problematic for reviews and geolocation. Snapshot schemas are easy to reason about and audit; repeated versions consume more space. This is acceptable for a historical solo project. A hash-derived schema plus advisory transaction lock prevents concurrent loader races. Raw immutability is a loader convention, not a database security guarantee; owner edits remain possible and reconciliation detects them.

## Validation and tooling

**Chosen:** standard-library CSV/Decimal/datetime, psycopg, pytest, and Ruff. No dataframe dependency is needed for field-preserving batch ingestion. pandas remains a suitable future exploration tool.

Great Expectations, dbt, or Airflow could add contracts, lineage and scheduling, but also increase the learning and deployment surface before the data is understood. Tests and explicit JSON reports cover this milestone. Executable SQL is maintained with its Python caller rather than duplicated in separately templated SQL files.

Profiles stream records but keep exact distinct/key sets for one table in memory. This is intentionally straightforward; memory grows with table cardinality. For much larger releases, use database aggregates or disk-backed sets. No approximate distinct statistics are silently substituted. Exact-row duplicate detection uses SHA-256 fingerprints (negligible collision risk) while candidate-key counts retain exact tuples.

## Quality findings vs load errors

Malformed CSV structure, unsupported headers, changed archives, or content mismatch stop the load. Missing values, duplicate business keys, orphan references and invalid field values are preserved and reported. Ingestion success never means quality validation passed.

Candidate primary keys and essential parent references are strict provisional gates. Review/ZIP candidate uniqueness, exact duplicate records, timestamp missingness and chronology anomalies are investigative profiles, not automatic deletion rules. Optional category references still report unmapped nonblank categories as failed checks. Any exception policy must be based on inspected records and documented before relaxing a gate.

## Temporal and financial assumptions

The source is historical. No freshness-to-today test is appropriate. Observed time ranges describe coverage, not live service health. Candidate timestamps are parsed as `%Y-%m-%d %H:%M:%S` without inventing a timezone; blanks remain distinguishable from invalid values. Chronology diagnostics compare available order event timestamps with purchase time, not a full lifecycle or status-specific consistency model.

Source monetary values are checked with exact Decimal and PostgreSQL numeric. Currency/unit semantics remain pending source documentation review. Conservation compares like measures; payments are not required to equal item-plus-freight totals. Malformed, missing and negative money are reported separately. No monetary business results are supplied without source data.

## Scope boundary

The original milestone 1 boundary excluded downstream application components; subsequently authorized work is recorded in PROGRESS.md and docs/architecture.md. The owner has supplied real local inspection and validation evidence. Milestone 1 is reviewed as complete with documented exception DQ-001, while the CLI preserves its original failed overall result. The owner subsequently authorized milestones 2–5, and this environment reproduced the source inventory and raw-data validation independently.

## Reviewed translation exception

Retain the existing strict relationship check and document DQ-001 rather than change it to a global warning or hard-code a successful count. A warning engine would change CLI semantics and require new regression tests; it is unnecessary to record this reviewed snapshot honestly. Future source changes require renewed review.
