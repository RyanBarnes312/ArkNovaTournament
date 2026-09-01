from pathlib import Path

from ark_nova_dashboard.card_data import (
    parse_animal_workbook,
    parse_bonuses,
    parse_enclosure,
    parse_requirements,
    parse_types,
)

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "card data" / "arknovaanimals_VM_v2.xlsx"


def test_requested_structures() -> None:
    assert parse_types("Predator/Bear") == ["predator", "bear"]
    assert parse_types("Sea Animal 2") == ["sea animal", "sea animal"]
    assert parse_requirements("Predator x2\nAnimals II") == {
        "predator": 2,
        "animals ii": 1,
    }
    assert parse_bonuses("9/2/1") == {
        "appeal": 9,
        "conservation": 2,
        "reputation": 1,
    }


def test_aquarium_enclosures_retain_conditions() -> None:
    assert parse_enclosure("(5) Aq 4 R") == {
        "size": 5,
        "water": 0,
        "rock": 1,
        "special_enclosure": [{"type": "aquarium", "spaces": 4}],
    }
    assert parse_enclosure("3RW / Aq 2") == {
        "size": 3,
        "water": 1,
        "rock": 1,
        "special_enclosure": [{"type": "aquarium", "spaces": 2}],
    }


def test_entire_animal_sheet_parses() -> None:
    cards = parse_animal_workbook(WORKBOOK)
    assert len(cards) == 160
    grizzly = next(card for card in cards if card["name"] == "Grizzly Bear")
    assert grizzly["requirements"] == {"predator": 2, "animals ii": 1}
