from ark_nova_dashboard.analytics import conservation_projects, game_results


def event(event_type: str, actor: str, details: dict, move: int = 1) -> dict:
    return {
        "event_type": event_type,
        "actor": actor,
        "details": details,
        "move_number": move,
        "turn_number": 2,
        "normalized_turn": 0.5,
        "turn_owner": actor,
    }


def test_project_is_joined_to_conservation_gain() -> None:
    game = {
        "events": [
            event("conservation_project", "Alice", {"project": "Birds", "slot": "second"}),
            event("conservation_gain", "Alice", {"source": "Birds", "amount": 4}),
        ]
    }

    assert conservation_projects(game)[0]["points"] == 4


def test_added_project_is_separated_from_base_projects() -> None:
    game = {
        "events": [
            event("conservation_project_added", "Alice", {"project": "Birds"}),
            event("conservation_project", "Alice", {"project": "Birds", "slot": "second"}),
            event("conservation_gain", "Alice", {"source": "Birds", "amount": 4}),
        ]
    }

    assert conservation_projects(game)[0]["project_type"] == "Additional"


def test_game_results_rank_and_normalize_scores() -> None:
    game = {
        "source": {"map_number": 2, "table": "B"},
        "events": [
            event(
                "final_score",
                "Alice",
                {"appeal": 80, "conservation_score": 20, "conservation": 15, "total": 100},
            ),
            event(
                "final_score",
                "Bob",
                {"appeal": 60, "conservation_score": 20, "conservation": 15, "total": 80},
            ),
        ],
    }

    results = game_results(game)

    assert results[0]["position"] == 1
    assert results[1]["position"] == 2
    assert results[1]["normalized_score"] == 0.8
