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

All charts (DA, Worldwide Traffic, US Traffic, Top 3 / Top 10 / Top 100, Top 3 Volume)
live in **one history CSV**, one line per chart and month.

1. **Load history**: upload last month's history CSV. (First time: skip this step.)
2. **Add a month**: upload this month's Semrush export, check the month, click *Add to all charts*.
   If the app warns that names don't match, fix the spelling with *Add or rename a competitor*.
3. **Choose a chart** and check its numbers in the table (you can correct values there).
4. **Chart**: choose competitors to show, our site, colors, and a y-axis per chart if needed. Then download:
   - one chart as PNG / SVG, or **all charts as a ZIP**
   - the **updated history CSV**. Keep it, because you'll upload it next month.

## History CSV format

```
metric,period,Fecon,Virnig,FAE Group
US Traffic,2026-01,16487,11431,8648
US Traffic,2026-02,15747,15112,10060
Top 100,2026-01,3369,5710,3089
```

- `metric` = chart name (Semrush's "Domain Overview" is called **DA**)
- `period` can be `2026-01`, `Jan 26` or `January 2026`
- numbers can be `3,369`, `3.4K` or `1.2M`. **Exact numbers give exact labels.**
- an empty cell = no data that month (a gap in the line)
- older files without a `metric` column still work (one chart, named after the file)

## Files

| File | What it does |
|---|---|
| `app.py` | The web page (Streamlit) |
| `chart.py` | `render_chart()`: draws the chart, prevents label overlaps. Colors in `DEFAULT_COLORS` |
| `data_loader.py` | Reads and checks CSV files, parses `K`/`M`/commas |
| `sample_data/` | Test data: `fecon_all_charts_history.csv` (US Traffic + Top 100), one Semrush export |
| `fonts/` | Liberation Sans, bundled so charts look the same on every PC |
| `reference/` | Original PRD, Manus's chart and code (for reference only) |

Test the chart code without the web page: `.venv\Scripts\python chart.py` writes test charts to `output/`.
