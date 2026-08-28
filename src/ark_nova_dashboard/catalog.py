from pathlib import Path
from typing import Literal

MAP_NUMBERS = tuple(range(1, 11))
TABLES = ("A", "B")
Table = Literal["A", "B"]


def raw_log_path(root: Path, map_number: int, table: Table) -> Path:
    """Return the canonical path for one unmodified BGA game log."""
    if map_number not in MAP_NUMBERS:
        raise ValueError(f"Map number must be between 1 and 10, got {map_number}")
    if table not in TABLES:
        raise ValueError(f"Table must be A or B, got {table}")
    return root / "data" / "raw" / f"map-{map_number:02d}" / f"table-{table.lower()}.txt"

