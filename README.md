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

## Password (required)

The app asks for a password. It is read from the **APP_PASSWORD** environment variable - it is never in the code.

- **Streamlit Cloud:** App → Settings → **Secrets** → add `APP_PASSWORD = "your-password"` → Save.
- **On your PC:** either set it when starting the app (PowerShell):
  ```
  $env:APP_PASSWORD = "your-password"
  .venv\Scripts\streamlit run app.py
  ```
  or create `.streamlit/secrets.toml` with `APP_PASSWORD = "your-password"` (this file is git-ignored).

After signing in, the browser stays signed in for 24 hours. Changing the password signs everyone out.

## Run

```
.venv\Scripts\streamlit run app.py
```

Then open http://localhost:8501

## Monthly workflow

The app has a sidebar (what's loaded, **Save data file**, **Sign out**) and 4 tabs:

| Tab | What for |
|---|---|
| **Dashboard** | Pick a chart: numbers at a glance (our site, rank, leader, biggest change), the chart, downloads, ranking |
| **Summary** | Our site across every chart |
| **Add data** | **Upload CSV** (a monthly export or a saved data file - recognised automatically), **Enter manually**, or **Edit existing** |
| **Settings** | Who is shown, our site, how names are shown, colors, y-axis |

Each month:

1. **Add data → Upload CSV**: last month's saved data file → **Open this file**. (First time: skip.)
2. **Add data → Upload CSV** again: this month's Semrush export → check the month → **Add**.
   No export? Use **Enter manually** and type the numbers.
3. **Dashboard**: check the charts → **Download chart** or **Download all charts (ZIP)**.
4. Sidebar → **Save data file**. Keep it - you upload it next month.

New here? Click **Try demo data** in the sidebar.

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
| `app.py` | The web page (Streamlit): sidebar + 4 tabs |
| `auth.py` | Password login (APP_PASSWORD) with a 24-hour sign-in cookie |
| `insights.py` | Dashboard numbers: rank, change vs last month, share, biggest move |
| `chart.py` | `render_chart()`: draws the chart, prevents label overlaps. Colors in `DEFAULT_COLORS` |
| `data_loader.py` | Reads and checks CSV files, parses `K`/`M`/commas |
| `sample_data/` | Test data: `fecon_all_charts_history.csv` (US Traffic + Top 100), Semrush exports (`TEST_` = dummy numbers) |
| `assets/` | Picture for the login page |
| `fonts/` | Liberation Sans, bundled so charts look the same on every PC |
| `reference/` | Original PRD, Manus's chart and code (for reference only) |

Test the chart code without the web page: `.venv\Scripts\python chart.py` writes test charts to `output/`.
