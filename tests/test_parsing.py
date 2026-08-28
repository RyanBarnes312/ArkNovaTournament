from pathlib import Path

import pytest

from ark_nova_dashboard.parsing import normalize_turn, parse_game_log


def test_normalize_turn() -> None:
    assert normalize_turn(10, 40) == 0.25


def test_normalize_turn_rejects_invalid_turn() -> None:
    with pytest.raises(ValueError):
        normalize_turn(41, 40)


def test_other_player_effect_retains_turn_owner(tmp_path: Path) -> None:
    log = tmp_path / "game.txt"
    log.write_text(
        "Move 1 :12:00:00\n"
        "Alice chooses action card SponsorsI with strength 5\n"
        "Move 2 :12:00:01\n"
        "Bob gains 2 money (Science Library)\n"
        "Move 3 :12:01:00\n"
        "Bob chooses action card CardsI with strength 5\n",
        encoding="utf-8",
    )

    events = parse_game_log(log)

    assert events[1].actor == "Bob"
    assert events[1].turn_number == 1
    assert events[1].turn_owner == "Alice"


def test_setup_move_has_no_turn_owner(tmp_path: Path) -> None:
    log = tmp_path / "game.txt"
    log.write_text(
        "Move 1 :12:00:00\n"
        "The colors of Alice, Bob have been chosen according to their preferences.\n",
        encoding="utf-8",
    )

    event = parse_game_log(log)[0]

    assert event.event_type == "setup"
    assert event.turn_number is None
    assert event.turn_owner is None
