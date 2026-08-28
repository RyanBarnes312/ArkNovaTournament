import html
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
from ark_nova_dashboard.pdf_report import build_tournament_pdf

COLOR_CONFIG = ROOT / "data" / "player-colors.json"
UNASSIGNED_COLOR = "#A7AFBD"

st.set_page_config(page_title="Ark Nova Tournament", page_icon="🦁", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #0f1728; color: #f7f8fb; }
    .st-key-top_navigation {
        background: #121d31; border: 1px solid #3b4657; border-radius: 12px;
        padding: 0.45rem 0.75rem; position: sticky; top: 0.5rem; z-index: 999;
        box-shadow: 0 7px 20px rgba(4, 9, 18, 0.32);
    }
    [data-testid="stMetric"] {
        background: #202b3c; border: 1px solid #3a4659; border-radius: 12px; padding: 12px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #1d2839; border-color: #3b4657; border-radius: 14px;
    }
    h1, h2, h3 { color: #f6e77f !important; }
    .mobile-card {
        background: #1d2839; border: 1px solid #3b4657; border-radius: 12px;
        margin: 0 0 10px 0; padding: 12px 14px;
    }
    .mobile-player { font-size: 1rem; font-weight: 700; }
    .mobile-rank { color: #f6e77f; font-size: 1.15rem; font-weight: 800; }
    .mobile-primary { display: flex; gap: 18px; margin-top: 9px; }
    .mobile-stat { color: #f7f8fb; font-size: 0.88rem; }
    .mobile-stat span { color: #8f99aa; display: block; font-size: 0.72rem; }
    .mobile-secondary { color: #8f99aa; font-size: 0.76rem; margin-top: 9px; }
    .mobile-game-pill {
        background: #111a2b; border-radius: 8px; display: inline-block;
        margin: 6px 5px 0 0; padding: 6px 9px;
    }
    .mobile-project-name { font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; }
    .mobile-added { color: #72e0a3; font-size: 0.7rem; font-weight: 600; }
    .mobile-project-score { align-items: center; display: flex; gap: 9px; margin-top: 7px; }
    .mobile-shield { height: 34px; position: relative; width: 30px; }
    .mobile-shield img { height: 34px; width: 30px; }
    .mobile-shield-value {
        color: #101827; font-size: 0.72rem; font-weight: 800; left: 0;
        position: absolute; text-align: center; top: 8px; width: 30px;
    }
    .mobile-project-detail { font-size: 0.8rem; }
    .mobile-project-detail span { color: #8f99aa; }
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.7rem 2rem !important; }
        h1 { font-size: 1.65rem !important; }
        h2 { font-size: 1.35rem !important; }
        h3 { font-size: 1.08rem !important; }
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
        [data-testid="column"] { flex: 1 1 100% !important; width: 100% !important; }
        [data-testid="stMetric"] { padding: 9px 11px; }
        .st-key-top_navigation { top: 0.25rem; padding: 0.25rem 0.45rem; }
        [data-testid="stDataFrame"] { overflow-x: auto; }
        .stPlotlyChart { overflow: hidden; }
    }
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


def mobile_project_html(projects: list[dict[str, Any]], colors: dict[str, str]) -> str:
    cards: list[str] = []
    project_names = list(dict.fromkeys(project["project"] for project in projects))
    for project_name in project_names:
        scores = [project for project in projects if project["project"] == project_name]
        added = scores[0]["project_type"] == "Additional"
        score_rows = []
        for score in scores:
            player = html.escape(str(score["player"]))
            progress = score["normalized_turn"] * 100
            score_rows.append(
                f'<div class="mobile-project-score">'
                f'<div class="mobile-shield"><img src="{shield_icon(colors[score["player"]])}">'
                f'<div class="mobile-shield-value">{score["points"] or "?"}</div></div>'
                f'<div class="mobile-project-detail"><b>{player}</b><br>'
                f'<span>Turn {score["turn_number"]} · {progress:.0f}% through game</span></div></div>'
            )
        badge = ' <span class="mobile-added">· ADDED</span>' if added else ""
        cards.append(
            f'<div class="mobile-card"><div class="mobile-project-name">'
            f'{html.escape(project_name)}{badge}</div>{"".join(score_rows)}</div>'
        )
    return "".join(cards)


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


def score_cards_html(scores: list[dict[str, Any]], colors: dict[str, str]) -> str:
    cards = []
    for position, score in enumerate(scores, start=1):
        player = str(score["player"])
        cards.append(
            f'<div class="mobile-card" style="border-left:4px solid {colors[player]}">'
            f'<div><span class="mobile-rank">#{position}</span> '
            f'<span class="mobile-player">{html.escape(player)}</span></div>'
            f'<div class="mobile-primary">'
            f'<div class="mobile-stat"><span>Final score</span>{score["total"]}</div>'
            f'<div class="mobile-stat"><span>Appeal</span>{score["appeal"]}</div>'
            f'<div class="mobile-stat"><span>Conservation</span>{score["conservation"]}</div>'
            f'</div></div>'
        )
    return "".join(cards)


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


def load_populated_games() -> list[dict[str, Any]]:
    games = []
    for map_number in MAP_NUMBERS:
        for table in TABLES:
            path = raw_log_path(ROOT, map_number, table)
            if path.exists() and path.stat().st_size:
                games.append(load_game(str(path), path.stat().st_mtime_ns, map_number, table))
    return games


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
    colors, missing_colors = player_colors(players)
    if missing_colors:
        st.warning(f"Missing global player colours: {', '.join(missing_colors)}")

    st.header("Tournament overview")

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
            "cumulative_position": "Tournament Score",
            "cumulative_normalized_score": "Tournament Normalized",
            "average_position": "Average position",
            "average_normalized_score": "Average normalized score",
        }
    )
    with st.container(key="mobile_standings"):
        standing_cards = []
        for _, row in summary.iterrows():
            player = str(row["Player"])
            standing_cards.append(
                f'<div class="mobile-card" style="border-left:4px solid {colors[player]}">'
                f'<div><span class="mobile-rank">#{row["Current rank"]}</span> '
                f'<span class="mobile-player">{html.escape(player)}</span></div>'
                f'<div class="mobile-primary">'
                f'<div class="mobile-stat"><span>Tournament Score</span>'
                f'{row["Tournament Score"]}</div>'
                f'<div class="mobile-stat"><span>Tournament Normalized</span>'
                f'{row["Tournament Normalized"]}</div></div>'
                f'<div class="mobile-secondary">Average position {row["Average position"]} · '
                f'Average normalized {row["Average normalized score"]}</div></div>'
            )
        st.markdown("".join(standing_cards), unsafe_allow_html=True)

    st.markdown("### Position by game")
    position_data = results.copy()
    position_data["result"] = position_data.apply(
        lambda row: f"{ordinal(int(row['position']))} · Table {row['table']}", axis=1
    )
    position_data["game"] = position_data["map_number"].map(lambda number: f"Map {number}")
    with st.container(key="mobile_positions"):
        position_cards = []
        for player in players:
            player_games = position_data[position_data["player"] == player].sort_values("map_number")
            pills = "".join(
                f'<span class="mobile-game-pill">Map {int(row["map_number"])} · '
                f'{html.escape(str(row["result"]))}</span>'
                for _, row in player_games.iterrows()
            )
            position_cards.append(
                f'<div class="mobile-card" style="border-left:4px solid {colors[player]}">'
                f'<div class="mobile-player">{html.escape(player)}</div>{pills}</div>'
            )
        st.markdown("".join(position_cards), unsafe_allow_html=True)


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
        st.markdown(score_cards_html(scores, colors), unsafe_allow_html=True)
    else:
        st.caption("Final scoring has not appeared in this log yet.")

    st.markdown("### Conservation project race")
    if projects:
        st.markdown(mobile_project_html(projects, colors), unsafe_allow_html=True)
    else:
        st.caption("No conservation-project scoring was found.")

st.title("Ark Nova Tournament")

navigation_options = ["Overview", *[f"Map {number}" for number in MAP_NUMBERS]]
with st.container(key="top_navigation"):
    navigation_column, download_column = st.columns([4, 1])
    with navigation_column:
        selected_page = st.selectbox(
            "Dashboard page",
            navigation_options,
            index=0,
            label_visibility="collapsed",
        )
    with download_column:
        pdf_games = load_populated_games()
        pdf_players = sorted(
            {player for game in pdf_games for player in game["summary"]["players"]}
        )
        pdf_colors, _ = player_colors(pdf_players)
        st.download_button(
            "Download PDF",
            data=build_tournament_pdf(pdf_games, pdf_colors),
            file_name="ark-nova-tournament.pdf",
            mime="application/pdf",
            width="stretch",
        )

if selected_page == "Overview":
    render_tournament()
else:
    selected_map = int(selected_page.removeprefix("Map "))

    st.header(f"Map {selected_map}")
    table_tabs = st.tabs([f"Table {table}" for table in TABLES])
    for tab, table in zip(table_tabs, TABLES, strict=True):
        with tab:
            render_table(selected_map, table)
