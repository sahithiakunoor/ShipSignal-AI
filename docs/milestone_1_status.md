# Milestone 1 review

**Status: complete with one documented data-quality exception for the owner's reviewed local snapshot. Historical milestone closeout; subsequent implementation is tracked in PROGRESS.md.**

## Evidence and scope

The project owner downloaded the real Olist files, ran inspection locally, loaded PostgreSQL successfully and supplied the generated dictionary, terminal counts and sole failed-check details in this conversation. The loaded raw schema is `raw_dbfbd3a2636389441845`. The original closeout relied on owner-supplied evidence. The current environment subsequently downloaded the official archive and independently reproduced its inventory, load and 56/57 validation result. It does not access the owner’s Mac database. File checksums, full snapshot ID, time ranges, exact monetary totals and run timestamps remain in the owner's local reports and are not fabricated here.

| Local command | Owner-reported outcome |
|---|---|
| `shipsignal inspect` | Generated the observed dictionary for nine tables |
| `shipsignal validate --source-only` | 34/35 checks passed |
| `shipsignal ingest` | `loaded`, schema `raw_dbfbd3a2636389441845` |
| `shipsignal validate` | 56/57 checks passed |

The only failure is the category translation lookup: 13 product rows across two nonblank source categories have no supplied translation. Another 610 products have a missing category, which is permitted by the relationship. See [DQ-001](data_quality_exceptions.md). The strict CLI remains unchanged and returns exit status 1; no failure has been relabeled as a pass.

## Implemented

- Installable modular Python package; CLI; versioned PostgreSQL Compose service; reproducible dependency versions.
- Local-only generated environment configuration, no embedded password fallback, ignored populated environment files.
- Strict CSV parsing; original-byte checksum archive; deterministic dataset snapshot identity; provenance manifest and observed column dictionary.
- Atomic PostgreSQL COPY across all tables; technical source-record numbers; snapshot metadata; loader locking and non-destructive reruns.
- Missingness, exact-row duplicates, candidate keys, date validity/ranges, selected chronology checks, monetary validity/sums, orphan records and parent multiplicity profiles.
- Source-quality gates and 22 database reconciliation checks for this nine-table release: row counts, all parsed fields, three monetary sums and safe order-grain joins.

## Observed source inventory

| Table | Records |
|---|---:|
| customers | 99,441 |
| geolocation | 1,000,163 |
| items | 112,650 |
| payments | 103,886 |
| reviews | 99,224 |
| orders | 99,441 |
| products | 32,951 |
| sellers | 3,095 |
| category_translation | 71 |

Source: [owner-supplied observed dictionary](observed_source_dictionary.md). These counts describe this snapshot, not universal constants embedded in validation.

## Software verification, distinct from real-data validation

The original stored [JUnit evidence](evidence/pytest.xml) contains 16 passing synthetic software tests. Three configuration regression tests were subsequently added; the credential-remediation run reported **19 passing tests**, including four PostgreSQL integration tests. Tests cover parsing, profiling, relationship defects, CLI behavior, rollback, idempotency, content preservation, monetary conservation, archive mutation, database edits and local configuration. The stored original XML is not represented as a 19-test report. The subsequent full application verification is recorded in PROGRESS.md; its final software suite has 36 passing tests. These implementation changes are local only pending explicit approval to publish.

Synthetic fixtures test behavior; they do not establish actual Olist findings. The owner's 56/57 data checks are a different validation run and must not be confused with 19 software tests.

## Review conclusions and limits

The supplied evidence supports faithful raw ingestion, tested order-level join conservation and the documented translation exception. It does not establish causal drivers, delivery KPIs, model scores, full event-lifecycle consistency, allowed domains, geographic plausibility, or future feature availability. Raw text types preserve evidence; typed core transformations remain deferred. Nonunique review IDs and ZIP prefixes are preserved, not deduplicated by assumption.

This document describes the scope of milestone 1 at its closeout. The owner subsequently authorized sequential application implementation; current dashboard, ML, retrieval, API and live-provider status are documented in PROGRESS.md and README.md.

## Learn and reproduce

The local authoritative files are `reports/inspection.json`, `reports/inspection.dictionary.md`, `reports/source-validation.json` and `reports/validation.json`; keep them locally with the unchanged source files. Never publish `.env`, credentials, tokens, raw reviews or arbitrary diagnostic logs. Runtime credentials belong only in ignored local configuration; do not publish them.
