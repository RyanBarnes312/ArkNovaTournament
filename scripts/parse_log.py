"""Convert one raw BGA text log to dashboard-ready JSON."""

import argparse
import json
from pathlib import Path

from ark_nova_dashboard.catalog import raw_log_path
from ark_nova_dashboard.parsing import game_data

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", dest="map_number", type=int, choices=range(1, 11), required=True)
    parser.add_argument("--table", choices=("A", "B"), required=True)
    parser.add_argument("--bga-table-id", type=int)
    args = parser.parse_args()

    source = raw_log_path(ROOT, args.map_number, args.table)
    if not source.read_text(encoding="utf-8-sig").strip():
        raise SystemExit(f"Raw log is empty: {source.relative_to(ROOT)}")

    destination = ROOT / "data" / "processed" / (
        f"map-{args.map_number:02d}-table-{args.table.lower()}.json"
    )
    parsed = game_data(source, args.map_number, args.table, args.bga_table_id)
    destination.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Parsed {parsed['summary']['event_count']} events across "
        f"{parsed['summary']['turn_count']} turns into {destination.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
