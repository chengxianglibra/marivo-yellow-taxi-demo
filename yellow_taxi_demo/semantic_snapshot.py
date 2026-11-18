"""Acquire bounded datasource evidence for the published semantic objects."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import marivo.datasource as md
import marivo.semantic as ms
from marivo.datasource.source import AuthoringScope

PREVIEW_MAX_ROWS = 1000
PREVIEW_TIMEOUT_SECONDS = 30
SETUP_REFS = (
    "entity:mobility.yellow_trips",
    "metric:mobility.fare_revenue",
    "relationship:mobility.trips_to_pickup_zones",
    "relationship:mobility.trips_to_dropoff_zones",
)


def _scope() -> AuthoringScope:
    return md.unpruned(max_rows=PREVIEW_MAX_ROWS, timeout_seconds=PREVIEW_TIMEOUT_SECONDS)


def _preview(catalog: ms.SemanticCatalog, entry: ms.SemanticObject) -> None:
    catalog.preview(entry, scope=_scope(), limit=10)


def _check_relationship(catalog: ms.SemanticCatalog, entry: ms.Relationship) -> None:
    definition = entry.definition
    entity_scopes = [
        (catalog.get(definition.from_entity), _scope()),
        (catalog.get(definition.to_entity), _scope()),
    ]
    report = catalog.validate(
        [entry],
        checks=[
            ms.source_check.relationship_cardinality(entry, expected=definition.cardinality),
            ms.source_check.relationship_matches(entry, side="from"),
        ],
        scope=entity_scopes,
    )
    if report.status != "current":
        report.show()
        raise RuntimeError(f"bounded relationship checks returned {report.status}")


def _preview_all(
    catalog: ms.SemanticCatalog, entries: Sequence[ms.SemanticObject]
) -> list[str]:
    failed: list[str] = []
    for entry in entries:
        try:
            if isinstance(entry, ms.Relationship):
                _check_relationship(catalog, entry)
            else:
                _preview(catalog, entry)
        except Exception as exc:
            failed.append(f"{entry.id}: {type(exc).__name__}: {exc}")
    return failed


def _entries(catalog: ms.SemanticCatalog, kind: str) -> list[ms.SemanticObject]:
    entries: list[ms.SemanticObject] = []
    cursor = None
    while True:
        page = catalog.search("", kind=kind, limit=100, cursor=cursor)
        entries.extend(page.items)
        cursor = page.next_cursor
        if cursor is None:
            return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="preview every published object")
    options = parser.parse_args()
    catalog = ms.load()
    if options.all:
        kinds = ("entity", "dimension", "time_dimension", "measure", "metric", "relationship")
        previewed = [entry for kind in kinds for entry in _entries(catalog, kind)]
    else:
        previewed = [catalog.get(ref) for ref in SETUP_REFS]
    failed = _preview_all(catalog, previewed)
    if failed:
        raise RuntimeError(f"semantic previews failed: {failed!r}")
    relationship_count = sum(isinstance(entry, ms.Relationship) for entry in previewed)
    print(
        f"semantic evidence acquired: {len(previewed) - relationship_count} bounded previews, "
        f"{relationship_count} bounded relationship checks "
        f"(max_rows={PREVIEW_MAX_ROWS}, timeout_seconds={PREVIEW_TIMEOUT_SECONDS} per scope)"
    )


if __name__ == "__main__":
    main()
