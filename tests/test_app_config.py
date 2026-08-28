import json
from pathlib import Path


def test_player_color_config_is_valid_json() -> None:
    path = Path(__file__).parents[1] / "data" / "player-colors.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["GwyndolinCinder"] == "#F5C542"
    assert data["BlackSheep42"] == "#F28C28"
