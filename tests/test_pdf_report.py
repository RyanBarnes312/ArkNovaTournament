from ark_nova_dashboard.pdf_report import build_tournament_pdf


def test_build_empty_tournament_pdf() -> None:
    report = build_tournament_pdf([], {})

    assert report.startswith(b"%PDF-")
    assert len(report) > 1_000
