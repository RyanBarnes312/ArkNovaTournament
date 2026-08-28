import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ark_nova_dashboard.models import GameEvent

MOVE_RE = re.compile(r"^Move (?P<number>\d+) :(?P<timestamp>.+)$")
TURN_START_RE = re.compile(
    r"^(?P<player>\S+) chooses action card (?P<card>\S+) with strength (?P<strength>\d+)$"
)
PROJECT_RE = re.compile(
    r"^(?P<player>\S+) supports a conservation project on the (?P<slot>\S+) slot : "
    r"(?P<project>.+)$"
)
PROJECT_ADDED_RE = re.compile(
    r"^(?P<player>\S+) (?:plays|buys) a new conservation project(?: from display)?: "
    r"(?P<project>.+)$"
)
MAP_BONUS_RE = re.compile(
    r"^(?P<player>\S+) (?P<operation>gains|loses|draws|takes|gets|receives) "
    r"(?P<value>.+?) \(map bonus space\)$"
)
CONSERVATION_RE = re.compile(
    r"^(?P<player>\S+) gains (?P<amount>\d+) conservation \((?P<source>.+)\)$"
)
FINAL_SCORE_RE = re.compile(
    r"^(?P<player>\S+) has (?P<appeal>-?\d+) and scores (?P<conservation_score>-?\d+) "
    r"for having (?P<conservation>-?\d+)\. (?P=player) scores (?P<total>-?\d+)\.$"
)
ACTOR_RE = re.compile(r"^(?P<actor>\S+)\s+")


def normalize_turn(turn: int, final_turn: int) -> float:
    """Express a turn as progress through the completed game, from 0.0 to 1.0."""
    if turn < 0:
        raise ValueError("turn cannot be negative")
    if final_turn <= 0:
        raise ValueError("final_turn must be positive")
    if turn > final_turn:
        raise ValueError("turn cannot be later than final_turn")
    return turn / final_turn


def _classify(text: str) -> tuple[str, dict[str, Any]]:
    if match := TURN_START_RE.match(text):
        return "turn_start", {
            "action_card": match["card"],
            "strength": int(match["strength"]),
        }
    if match := PROJECT_RE.match(text):
        return "conservation_project", {
            "project": match["project"],
            "slot": match["slot"],
        }
    if match := PROJECT_ADDED_RE.match(text):
        return "conservation_project_added", {"project": match["project"]}
    if match := MAP_BONUS_RE.match(text):
        return "map_bonus", {
            "operation": match["operation"],
            "value": match["value"],
        }
    if match := CONSERVATION_RE.match(text):
        return "conservation_gain", {
            "amount": int(match["amount"]),
            "source": match["source"],
        }
    if match := FINAL_SCORE_RE.match(text):
        return "final_score", {
            "appeal": int(match["appeal"]),
            "conservation_score": int(match["conservation_score"]),
            "conservation": int(match["conservation"]),
            "total": int(match["total"]),
        }
    if text == "End of game":
        return "game_end", {}
    if text.startswith("End of game triggered:"):
        return "game_end_triggered", {}
    if "colors of " in text and "have been chosen" in text:
        return "setup", {"phase": "colors"}
    if "draft phase" in text:
        return "setup", {"phase": "action_card_draft"}
    return "log", {}


def parse_game_log(path: Path) -> list[GameEvent]:
    """Parse BGA text while retaining move, turn owner, and per-line actor.

    A turn begins at ``chooses action card``. Effects by other players remain
    attached to that turn through ``turn_owner`` while their own name is retained
    in ``actor``. Setup lines before the first action have no turn owner.
    """
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    known_players = {
        match["player"]
        for line in lines
        if (match := TURN_START_RE.match(line.strip()))
    }
    known_players.update(
        match["player"]
        for line in lines
        if (match := FINAL_SCORE_RE.match(line.strip()))
    )

    events: list[GameEvent] = []
    move_number: int | None = None
    timestamp = ""
    turn_number = 0
    turn_owner: str | None = None

    for source_line in lines:
        text = source_line.strip()
        if not text:
            continue
        if move_match := MOVE_RE.match(text):
            move_number = int(move_match["number"])
            timestamp = move_match["timestamp"].strip()
            continue
        if move_number is None:
            raise ValueError(f"Log content appears before the first Move header: {text}")

        if turn_match := TURN_START_RE.match(text):
            turn_number += 1
            turn_owner = turn_match["player"]

        event_type, details = _classify(text)
        actor_match = ACTOR_RE.match(text)
        possible_actor = actor_match["actor"] if actor_match else None
        actor = possible_actor if possible_actor in known_players else None

        events.append(
            GameEvent(
                move_number=move_number,
                timestamp=timestamp,
                sequence=len(events) + 1,
                text=text,
                event_type=event_type,
                actor=actor,
                turn_number=turn_number or None,
                turn_owner=turn_owner,
                details=details,
            )
        )

    return events


def game_data(path: Path, map_number: int, table: str, bga_table_id: int | None = None) -> dict[str, Any]:
    events = parse_game_log(path)
    final_turn = max((event.turn_number or 0 for event in events), default=0)
    players = sorted({event.turn_owner for event in events if event.turn_owner})

    serialized_events = []
    for event in events:
        item = asdict(event)
        item["normalized_turn"] = (
            normalize_turn(event.turn_number, final_turn) if event.turn_number else None
        )
        serialized_events.append(item)

    return {
        "source": {
            "map_number": map_number,
            "table": table,
            "bga_table_id": bga_table_id,
            "raw_log": path.as_posix(),
        },
        "summary": {
            "players": players,
            "turn_count": final_turn,
            "event_count": len(events),
            "first_move": events[0].move_number if events else None,
            "last_move": events[-1].move_number if events else None,
        },
        "events": serialized_events,
    }
