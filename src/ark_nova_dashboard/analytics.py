from typing import Any


def conservation_projects(game: dict[str, Any]) -> list[dict[str, Any]]:
    """Join each project support to its matching conservation award."""
    events = game["events"]
    additional_projects = {
        event["details"]["project"]
        for event in events
        if event["event_type"] == "conservation_project_added"
    }
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if event["event_type"] != "conservation_project":
            continue

        project = event["details"]["project"]
        points = None
        for candidate in events[index + 1 :]:
            if candidate["turn_number"] != event["turn_number"]:
                break
            if (
                candidate["event_type"] == "conservation_gain"
                and candidate["actor"] == event["actor"]
                and candidate["details"]["source"] == project
            ):
                points = candidate["details"]["amount"]
                break

        rows.append(
            {
                "player": event["actor"],
                "project": project,
                "project_type": "Additional" if project in additional_projects else "Base",
                "slot": event["details"]["slot"],
                "points": points,
                "move_number": event["move_number"],
                "turn_number": event["turn_number"],
                "normalized_turn": event["normalized_turn"],
            }
        )
    return rows


def final_scores(game: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"player": event["actor"], **event["details"]}
        for event in game["events"]
        if event["event_type"] == "final_score"
    ]
    return sorted(rows, key=lambda row: row["total"], reverse=True)


def game_results(game: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ranked, table-normalized results for one completed game."""
    scores = final_scores(game)
    if not scores:
        return []

    top_score = scores[0]["total"]
    previous_score: int | None = None
    position = 0
    results: list[dict[str, Any]] = []
    for index, score in enumerate(scores, start=1):
        if score["total"] != previous_score:
            position = index
            previous_score = score["total"]
        results.append(
            {
                "map_number": game["source"]["map_number"],
                "table": game["source"]["table"],
                "player": score["player"],
                "position": position,
                "score": score["total"],
                "top_score": top_score,
                "normalized_score": score["total"] / top_score if top_score else None,
            }
        )
    return results
