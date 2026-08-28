import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ark_nova_dashboard.analytics import conservation_projects, final_scores, game_results
from ark_nova_dashboard.catalog import MAP_NUMBERS, TABLES, raw_log_path
from ark_nova_dashboard.parsing import game_data

COLOR_CONFIG = ROOT / "data" / "player-colors.json"
UNASSIGNED_COLOR = "#A7AFBD"

st.set_page_config(page_title="Ark Nova Tournament", page_icon="🦁", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #0f1728; color: #f7f8fb; }
    [data-testid="stSidebar"] { background: #121d31; }
    [data-testid="stMetric"] {
        background: #202b3c; border: 1px solid #3a4659; border-radius: 12px; padding: 12px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #1d2839; border-color: #3b4657; border-radius: 14px;
    }
    h1, h2, h3 { color: #f6e77f !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_game(path_string: str, modified_ns: int, map_number: int, table: str) -> dict[str, Any]:
    del modified_ns  # Included in the cache key so pasted logs automatically refresh.
    return game_data(Path(path_string), map_number, table)


def player_colors(players: list[str]) -> tuple[dict[str, str], list[str]]:
    """Load dashboard-wide BGA colours without inferring missing assignments."""
    configured = json.loads(COLOR_CONFIG.read_text(encoding="utf-8")) if COLOR_CONFIG.exists() else {}
    missing = [player for player in players if not configured.get(player)]
    return {player: configured.get(player) or UNASSIGNED_COLOR for player in players}, missing


def shield_icon(color: str) -> str:
    """Return a solid, standard shield as an embeddable SVG data URI."""
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 56">
      <path d="M24 2L44 9V24C44 38 35 49 24 54C13 49 4 38 4 24V9L24 2Z"
            fill="{color}" stroke="#101827" stroke-width="3" stroke-linejoin="round"/>
    </svg>
    """
    return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


def project_chart(rows: list[dict[str, Any]], colors: dict[str, str]) -> go.Figure:
    figure = go.Figure()
    projects = list(dict.fromkeys(row["project"] for row in rows))
    project_positions = {project: index for index, project in enumerate(projects)}
    project_types = {row["project"]: row["project_type"] for row in rows}

    for project, position in project_positions.items():
        if project_types[project] == "Additional":
            figure.add_hrect(
                y0=position - 0.48,
                y1=position + 0.48,
                fillcolor="rgba(114, 224, 163, 0.07)",
                line_width=0,
                layer="below",
            )

    for player, color in colors.items():
        player_rows = [row for row in rows if row["player"] == player]
        if not player_rows:
            continue

        for row in player_rows:
            x = row["normalized_turn"] * 100
            y = project_positions[row["project"]]
            figure.add_layout_image(
                source=shield_icon(color),
                x=x,
                y=y,
                xref="x",
                yref="y",
                sizex=5.2,
                sizey=1.05,
                xanchor="center",
                yanchor="middle",
                sizing="contain",
                layer="above",
            )
            figure.add_annotation(
                x=x,
                y=y - 0.04,
                xref="x",
                yref="y",
                text=str(row["points"] or "?"),
                showarrow=False,
                font={"color": "#101827", "size": 13, "weight": 700},
            )

        figure.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                name=player,
                marker={"color": color, "size": 12, "symbol": "square"},
                legendgroup=player,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[row["normalized_turn"] * 100 for row in player_rows],
                y=[project_positions[row["project"]] - 0.04 for row in player_rows],
                mode="markers",
                name=player,
                marker={"color": "rgba(0,0,0,0)", "size": 34},
                customdata=[
                    [
                        row["project"],
                        row["turn_number"],
                        row["move_number"],
                        row["slot"],
                        row["points"],
                    ]
                    for row in player_rows
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>%{fullData.name}<br>Game progress: %{x:.1f}%"
                    "<br>Turn: %{customdata[1]}<br>BGA move: %{customdata[2]}"
                    "<br>Slot: %{customdata[3]}<br>Conservation: %{customdata[4]}<extra></extra>"
                ),
                legendgroup=player,
                showlegend=False,
            )
        )
    figure.update_layout(
        height=max(330, 64 + len(projects) * 64),
        margin={"l": 8, "r": 12, "t": 15, "b": 15},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111a2b",
        font={"color": "#f7f8fb"},
        legend={"orientation": "h", "y": 1.13, "x": 0},
        xaxis={
            "title": "Progress through completed game",
            "range": [-3, 103],
            "ticksuffix": "%",
            "gridcolor": "#2d394c",
        },
        yaxis={
            "title": None,
            "tickmode": "array",
            "tickvals": list(range(len(projects))),
            "ticktext": [
                f"{project}  · added" if project_types[project] == "Additional" else project
                for project in projects
            ],
            "range": [-0.95, len(projects) - 0.25],
            "gridcolor": "#2d394c",
        },
    )
    return figure


def score_chart(scores: list[dict[str, Any]], colors: dict[str, str]) -> go.Figure:
    figure = go.Figure(
        go.Bar(
            x=[score["total"] for score in scores],
            y=[score["player"] for score in scores],
            orientation="h",
            marker_color=[colors[score["player"]] for score in scores],
            text=[score["total"] for score in scores],
            textposition="inside",
            customdata=[[score["appeal"], score["conservation"]] for score in scores],
            hovertemplate=(
                "<b>%{y}</b><br>Final score: %{x}<br>Appeal: %{customdata[0]}"
                "<br>Conservation: %{customdata[1]}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=245,
        margin={"l": 8, "r": 12, "t": 10, "b": 15},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111a2b",
        font={"color": "#f7f8fb"},
        xaxis={"title": "Final score", "gridcolor": "#2d394c"},
        yaxis={"title": None, "autorange": "reversed"},
        showlegend=False,
    )
    return figure


def load_tournament_results() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for map_number in MAP_NUMBERS:
        for table in TABLES:
            path = raw_log_path(ROOT, map_number, table)
            if not path.exists() or path.stat().st_size == 0:
                continue
            game = load_game(str(path), path.stat().st_mtime_ns, map_number, table)
            rows.extend(game_results(game))
    return pd.DataFrame(rows)


def ordinal(position: int) -> str:
    suffix = (
        "th"
        if 10 <= position % 100 <= 20
        else {1: "st", 2: "nd", 3: "rd"}.get(position % 10, "th")
    )
    return f"{position}{suffix}"


def render_tournament() -> None:
    results = load_tournament_results()
    if results.empty:
        st.info("No completed tournament games have been added yet.")
        return

    players = sorted(results["player"].unique().tolist())
    _colors, missing_colors = player_colors(players)
    if missing_colors:
        st.warning(f"Missing global player colours: {', '.join(missing_colors)}")

    st.header("Tournament overview")
    st.caption("Results follow each player across Table A and Table B.")

    summary = (
        results.groupby("player", as_index=False)
        .agg(
            cumulative_position=("position", "sum"),
            cumulative_normalized_score=("normalized_score", "sum"),
            average_position=("position", "mean"),
            average_normalized_score=("normalized_score", "mean"),
        )
        .sort_values(
            ["cumulative_position", "cumulative_normalized_score"],
            ascending=[True, False],
        )
        .reset_index(drop=True)
    )
    current_ranks: list[int] = []
    previous_result: tuple[int, float] | None = None
    current_rank = 0
    for index, row in summary.iterrows():
        result = (int(row["cumulative_position"]), float(row["cumulative_normalized_score"]))
        if result != previous_result:
            current_rank = index + 1
            previous_result = result
        current_ranks.append(current_rank)
    summary.insert(0, "current_rank", current_ranks)

    summary["cumulative_normalized_score"] = summary["cumulative_normalized_score"].map(
        lambda value: f"{value:.3f}"
    )
    summary["average_position"] = summary["average_position"].map(lambda value: f"{value:.2f}")
    summary["average_normalized_score"] = summary["average_normalized_score"].map(
        lambda value: f"{value:.1%}"
    )
    summary = summary.rename(
        columns={
            "current_rank": "Current rank",
            "player": "Player",
            "cumulative_position": "Cumulative finishing position",
            "cumulative_normalized_score": "Cumulative normalized score",
            "average_position": "Average position",
            "average_normalized_score": "Average normalized score",
        }
    )
    styled_summary = summary.style.set_properties(
        subset=["Average position", "Average normalized score"],
        color="#8F99AA",
    ).set_properties(
        subset=["Current rank", "Cumulative finishing position", "Cumulative normalized score"],
        **{"font-weight": "700"},
    )
    st.dataframe(
        styled_summary,
        hide_index=True,
        width="stretch",
    )

    st.markdown("### Position by game")
    position_data = results.copy()
    position_data["result"] = position_data.apply(
        lambda row: f"{ordinal(int(row['position']))} · Table {row['table']}", axis=1
    )
    position_data["game"] = position_data["map_number"].map(lambda number: f"Map {number}")
    matrix = position_data.pivot(index="player", columns="game", values="result").reset_index()
    st.dataframe(matrix.rename(columns={"player": "Player"}), hide_index=True, width="stretch")


def render_table(map_number: int, table: str) -> None:
    path = raw_log_path(ROOT, map_number, table)
    if not path.exists() or path.stat().st_size == 0:
        st.info(f"Waiting for `{path.relative_to(ROOT)}`")
        return

    try:
        game = load_game(str(path), path.stat().st_mtime_ns, map_number, table)
    except ValueError as error:
        st.error(f"Could not parse this log: {error}")
        return

    summary = game["summary"]
    projects = conservation_projects(game)
    scores = final_scores(game)
    colors, missing_colors = player_colors(summary["players"])

    if missing_colors:
        st.warning(
            "Player colours are not present in the BGA text log. Add them to "
            f"`data/player-colors.json`: {', '.join(missing_colors)}"
        )

    winner = scores[0]["player"] if scores else "Game in progress"
    player_count = len(summary["players"])
    average_turns = summary["turn_count"] / player_count if player_count else 0
    metrics = st.columns(2)
    metrics[0].metric("Winner", winner)
    metrics[1].metric("Average turns per player", f"{average_turns:.2f}")

    st.markdown("### Final standings")
    if scores:
        st.plotly_chart(score_chart(scores, colors), width="stretch", config={"displayModeBar": False})
    else:
        st.caption("Final scoring has not appeared in this log yet.")

    st.markdown("### Conservation project race")
    if projects:
        st.plotly_chart(
            project_chart(projects, colors),
            width="stretch",
            config={"displayModeBar": False},
        )
    else:
        st.caption("No conservation-project scoring was found.")

    with st.expander("Parsed event data"):
        event_frame = pd.DataFrame(game["events"])
        st.dataframe(
            event_frame[
                ["move_number", "turn_number", "turn_owner", "actor", "event_type", "text"]
            ],
            hide_index=True,
            width="stretch",
        )


st.title("Ark Nova Tournament")
st.caption("Two-table promotion and relegation tournament")

view = st.sidebar.radio("Dashboard view", ("Tournament overview", "Game detail"))

if view == "Tournament overview":
    render_tournament()
else:
    selected_map = st.sidebar.selectbox(
        "Tournament map",
        options=MAP_NUMBERS,
        index=1,
        format_func=lambda number: f"Map {number}",
    )

    st.header(f"Map {selected_map}")
    table_tabs = st.tabs([f"Table {table}" for table in TABLES])
    for tab, table in zip(table_tabs, TABLES, strict=True):
        with tab:
            render_table(selected_map, table)
