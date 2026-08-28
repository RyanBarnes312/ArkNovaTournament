from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ConservationScore:
    player: str
    project: str
    spaces: int
    turn: int
    normalized_time: float


@dataclass(frozen=True, slots=True)
class MapBonus:
    player: str
    label: str
    value: int | float | str
    turn: int | None = None


@dataclass(frozen=True, slots=True)
class GameEvent:
    """One visible BGA log line with both move and gameplay-turn context."""

    move_number: int
    timestamp: str
    sequence: int
    text: str
    event_type: str
    actor: str | None
    turn_number: int | None
    turn_owner: str | None
    details: dict[str, Any]
