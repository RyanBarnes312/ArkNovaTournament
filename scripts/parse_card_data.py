import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ark_nova_dashboard.card_data import parse_animal_workbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Ark Nova animal card XLSX data to JSON")
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=ROOT / "data" / "card data" / "arknovaanimals_VM_v2.xlsx",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "cards" / "animals.json",
    )
    arguments = parser.parse_args()

    cards = parse_animal_workbook(arguments.source)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(cards, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(cards)} animal cards to {arguments.output}")


if __name__ == "__main__":
    main()
