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

The app has a sidebar for your **data file** and 5 tabs:

| Tab | What for |
|---|---|
| 📊 **Dashboard** | Pick a chart (one click), see KPI tiles (our site, rank, leader, biggest move), the chart, downloads and a leaderboard |
| 🏆 **Summary** | Our site across every chart at a glance |
| ➕ **Add month** | Upload this month's Semrush export - it updates every chart at once |
| ✏️ **Fix data** | Correct a number, rename a competitor spelled differently |
| ⚙️ **Style** | Who is shown, our site, how names are shown, colors, y-axis |

Each month:

1. Sidebar → **Open data file**: last month's file. (First time: skip.)
2. **➕ Add month** → upload the Semrush export → check the month → **Add**.
3. **📊 Dashboard** → check the charts → **Download this chart** or **All charts (ZIP)**.
4. Sidebar → **💾 Save data file**. Keep it - you open it next month.

New here? Click **✨ Try demo data** in the sidebar.

## Data file format

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
| `app.py` | The web page (Streamlit): sidebar + 5 tabs |
| `insights.py` | Dashboard numbers: rank, change vs last month, share, biggest move |
| `chart.py` | `render_chart()`: draws the chart, prevents label overlaps. Colors in `DEFAULT_COLORS` |
| `data_loader.py` | Reads and checks CSV files, parses `K`/`M`/commas |
| `sample_data/` | Test data: `fecon_all_charts_history.csv` (US Traffic + Top 100), one Semrush export |
| `fonts/` | Liberation Sans, bundled so charts look the same on every PC |
| `reference/` | Original PRD, Manus's chart and code (for reference only) |

Test the chart code without the web page: `.venv\Scripts\python chart.py` writes test charts to `output/`.
