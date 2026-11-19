"""Quality gates are separate from ingestion: imperfect raw data remains preservable."""

from .contracts import DATES, KEYS, MONEY


def quality_checks(manifest):
    checks = [
        {
            "check": "expected_table_coverage",
            "passed": not manifest["missing_tables"],
            "missing": manifest["missing_tables"],
        }
    ]
    for table, info in manifest["tables"].items():
        checks.append({"check": f"{table}.nonempty", "passed": info["rows"] > 0})
        if table in KEYS:
            key = info["keys"].get(",".join(KEYS[table]))
            checks.append(
                {
                    "check": f"{table}.provisional_primary_key",
                    "passed": bool(
                        key is not None
                        and key["missing_rows"] == 0
                        and key["duplicate_excess_rows"] == 0
                    ),
                    "detail": key,
                }
            )
        for column in DATES.get(table, []):
            profile = info["timestamps"].get(column)
            checks.append(
                {
                    "check": f"{table}.{column}.timestamp_parse",
                    "passed": profile is not None and profile["invalid"] == 0,
                    "detail": profile,
                }
            )
        for column in MONEY.get(table, []):
            profile = info["money"].get(column)
            checks.append(
                {
                    "check": f"{table}.{column}.valid_nonmissing_nonnegative_money",
                    "passed": profile is not None
                    and not any(profile[k] for k in ("invalid", "missing", "negative")),
                    "detail": profile,
                }
            )
    for relationship in manifest["relationships"]:
        checks.append(
            {
                "check": f"{relationship['child']}.{relationship['column']}.relationship",
                "passed": relationship["status"] == "checked"
                and relationship["orphan_rows"] == 0
                and relationship["parent_missing_rows"] == 0
                and relationship["parent_duplicate_excess_rows"] == 0
                and (relationship["nullable"] or relationship["missing_child_rows"] == 0),
                "detail": relationship,
            }
        )
    return checks
