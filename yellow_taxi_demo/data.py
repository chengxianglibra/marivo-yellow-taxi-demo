"""The pickup-time analysis window and a remote source inspection entry point."""

from datetime import date
from typing import cast

import marivo.datasource as md
import marivo.semantic as ms

SOURCE_MONTH = "2025-12"
MONTH_START = date.fromisoformat(f"{SOURCE_MONTH}-01")
MONTH_END = date(MONTH_START.year + (MONTH_START.month == 12), MONTH_START.month % 12 + 1, 1)


def main() -> None:
    catalog = ms.load()
    datasource = ms.ref.datasource("cloudfront")
    for name in ("yellow_trips", "pickup_zones"):
        entity = cast(ms.Entity, catalog.get(f"entity:mobility.{name}"))
        md.inspect(datasource, entity.definition.source).show()


if __name__ == "__main__":
    main()
