# Ark Nova Tournament Dashboard

A Python/Streamlit dashboard for a ten-map Ark Nova tournament played across
Table A and Table B on Board Game Arena.

## Raw logs

Place the unmodified BGA text exports in the matching files below:

```text
data/raw/map-01/table-a.txt
data/raw/map-01/table-b.txt
...
data/raw/map-10/table-a.txt
data/raw/map-10/table-b.txt
```

The checked-in log files are intentionally empty. Generated structured data will
live under `data/processed/`; raw logs should never be edited by the parser.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
streamlit run app.py
```

The initial app shows the project structure and flags which logs have been added.
Parsing and map-specific scoring rules will be implemented against representative
BGA logs.

## Player colours

BGA's pasted text logs say that colours were selected but do not include the
player-to-colour mapping. Record each BGA username's dashboard-wide hex colour in
`data/player-colors.json`. Missing colours remain neutral grey rather than being
guessed.
