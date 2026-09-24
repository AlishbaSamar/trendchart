# Competitor Trend Chart

Internal tool: upload SEO competitor data, get the monthly trend chart (PNG / SVG).
Replaces the Manus workflow. Same data in = same chart out, every time.

Note: `sample_data/` and `reference/` contain real competitor numbers used for testing.

## First-time setup (Windows)

```
cd C:\Users\PMLS\Projects\ChartMaker
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Run

```
.venv\Scripts\streamlit run app.py
```

Then open http://localhost:8501

## Monthly workflow

1. **Load history**: upload last month's history CSV for this chart (e.g. `fecon_top100_history.csv`).
2. **Add a month**: upload this month's Semrush export, pick the metric (e.g. Top 100), check the month, click *Add*.
   If the app warns that names don't match, fix the spelling with *Add or rename a competitor*.
3. **Check the data** in the table and correct any value.
4. **Chart**: choose competitors to show, our site, axis and colors. Then download:
   - the PNG / SVG for the report
   - the **updated history CSV**. Keep it, because you'll upload it next month.

Keep one history CSV per chart (traffic, Top 100, Top 3 volume...) in a shared folder.

## History CSV format

```
period,Fecon,Virnig,FAE Group
2026-01,3369,5710,3089
2026-02,3534,5758,3234
```

- `period` can be `2026-01`, `Jan 26` or `January 2026`
- numbers can be `3,369`, `3.4K` or `1.2M`. **Exact numbers give exact labels.**
- an empty cell = no data that month (a gap in the line)
- a long format `period,series,value` is also accepted

## Files

| File | What it does |
|---|---|
| `app.py` | The web page (Streamlit) |
| `chart.py` | `render_chart()`: draws the chart, prevents label overlaps. Colors in `DEFAULT_COLORS` |
| `data_loader.py` | Reads and checks CSV files, parses `K`/`M`/commas |
| `sample_data/` | Test data (Top 100 and traffic histories, one Semrush export) |
| `fonts/` | Liberation Sans, bundled so charts look the same on every PC |
| `reference/` | Original PRD, Manus's chart and code (for reference only) |

Test the chart code without the web page: `.venv\Scripts\python chart.py` writes test charts to `output/`.
