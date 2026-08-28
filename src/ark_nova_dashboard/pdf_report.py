from collections import defaultdict
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .analytics import conservation_projects, final_scores, game_results

BACKGROUND = colors.HexColor("#0F1728")
CARD = colors.HexColor("#1D2839")
BORDER = colors.HexColor("#3B4657")
TEXT = colors.HexColor("#F7F8FB")
MUTED = colors.HexColor("#A7AFBD")
ACCENT = colors.HexColor("#F6E77F")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PdfTitle", parent=base["Title"], textColor=ACCENT, fontSize=22, leading=26
        ),
        "heading": ParagraphStyle(
            "PdfHeading", parent=base["Heading2"], textColor=ACCENT, fontSize=15, leading=19
        ),
        "card": ParagraphStyle(
            "PdfCard", parent=base["BodyText"], textColor=TEXT, fontSize=9, leading=13
        ),
        "small": ParagraphStyle(
            "PdfSmall", parent=base["BodyText"], textColor=MUTED, fontSize=8, leading=11
        ),
        "footer": ParagraphStyle(
            "PdfFooter", parent=base["BodyText"], textColor=MUTED, fontSize=7, alignment=TA_CENTER
        ),
    }


def _background(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFillColor(BACKGROUND)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(A4[0] / 2, 8 * mm, f"Ark Nova Tournament  |  Page {document.page}")
    canvas.restoreState()


def _card(body: str, color: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(body, styles["card"])]], colWidths=[174 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD),
                ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(color)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def build_tournament_pdf(games: list[dict[str, Any]], player_colors: dict[str, str]) -> bytes:
    """Build a static PDF containing the overview and every populated game."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Ark Nova Tournament",
    )
    styles = _styles()
    story: list[Any] = [Paragraph("Ark Nova Tournament", styles["title"]), Spacer(1, 5 * mm)]

    results = [row for game in games for row in game_results(game)]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[row["player"]].append(row)

    ranking = sorted(
        grouped.items(),
        key=lambda item: (
            sum(row["position"] for row in item[1]),
            -sum(row["normalized_score"] for row in item[1]),
        ),
    )
    story.append(Paragraph("Tournament overview", styles["heading"]))
    for rank, (player, rows) in enumerate(ranking, start=1):
        tournament_score = sum(row["position"] for row in rows)
        tournament_normalized = sum(row["normalized_score"] for row in rows)
        average_position = tournament_score / len(rows)
        average_normalized = tournament_normalized / len(rows)
        game_line = " &nbsp; | &nbsp; ".join(
            f'Map {row["map_number"]}: {row["position"]} (Table {row["table"]})'
            for row in sorted(rows, key=lambda row: row["map_number"])
        )
        body = (
            f'<b>#{rank} &nbsp; {player}</b><br/>'
            f'Tournament Score: <b>{tournament_score}</b> &nbsp; &nbsp; '
            f'Tournament Normalized: <b>{tournament_normalized:.3f}</b><br/>'
            f'<font color="#A7AFBD">Average position: {average_position:.2f} &nbsp; | &nbsp; '
            f'Average normalized: {average_normalized:.1%}<br/>{game_line}</font>'
        )
        story.extend([_card(body, player_colors.get(player, "#A7AFBD"), styles), Spacer(1, 2.5 * mm)])

    for game in sorted(games, key=lambda item: (item["source"]["map_number"], item["source"]["table"])):
        source = game["source"]
        summary = game["summary"]
        scores = final_scores(game)
        projects = conservation_projects(game)
        story.extend(
            [
                PageBreak(),
                Paragraph(f'Map {source["map_number"]} - Table {source["table"]}', styles["title"]),
                Paragraph(
                    f'Winner: <b>{scores[0]["player"] if scores else "Game in progress"}</b> &nbsp; | &nbsp; '
                    f'Turns: {summary["turn_count"]}',
                    styles["card"],
                ),
                Spacer(1, 4 * mm),
                Paragraph("Final standings", styles["heading"]),
            ]
        )
        for position, score in enumerate(scores, start=1):
            player = score["player"]
            body = (
                f'<b>#{position} &nbsp; {player}</b><br/>Final score: <b>{score["total"]}</b>'
                f' &nbsp; | &nbsp; Appeal: {score["appeal"]}'
                f' &nbsp; | &nbsp; Conservation: {score["conservation"]}'
            )
            story.extend([_card(body, player_colors.get(player, "#A7AFBD"), styles), Spacer(1, 2 * mm)])

        story.extend([Spacer(1, 2 * mm), Paragraph("Conservation project race", styles["heading"])])
        by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for project in projects:
            by_project[project["project"]].append(project)
        for project_name, project_rows in by_project.items():
            project_type = project_rows[0]["project_type"]
            lines = []
            for row in project_rows:
                lines.append(
                    f'<b>{row["player"]}</b>: {row["points"] or "?"} conservation, '
                    f'turn {row["turn_number"]}, {row["normalized_turn"]:.0%} through game'
                )
            body = f'<b>{project_name}</b>{" - added" if project_type == "Additional" else ""}<br/>'
            body += "<br/>".join(lines)
            story.extend(
                [KeepTogether(_card(body, "#72E0A3" if project_type == "Additional" else "#A7AFBD", styles)), Spacer(1, 2 * mm)]
            )

    document.build(story, onFirstPage=_background, onLaterPages=_background)
    return output.getvalue()
