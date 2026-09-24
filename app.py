"""
app.py - the web page. Run it with:

    streamlit run app.py

How Streamlit works (the one thing to know):
  Every time the user clicks or types anything, Streamlit runs this WHOLE
  file again from top to bottom. Values that must survive between runs are
  kept in `st.session_state` (a dictionary that Streamlit remembers).
  Button "callbacks" (on_click=...) run BEFORE that rerun, so they can
  change the data and switch tabs before the page is drawn.

Layout:
  Sidebar           your data file: open / try demo / save
  📊 Dashboard      pick a chart -> KPI tiles, chart, downloads, leaderboard
  🏆 Summary        our site across every chart
  ➕ Add month      upload this month's Semrush export
  ✏️ Fix data       correct numbers, rename competitors
  ⚙️ Style          who is shown, our site, names, colors, y-axis
"""

import io
import re
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from chart import ChartSettings, auto_axis, pick_colors, render_chart
from data_loader import (
    DataError,
    add_month_all,
    histories_to_csv,
    load_histories,
    load_history,
    load_semrush_month,
    period_label,
)
from insights import biggest_mover, fmt, fmt_change, latest_months, leaderboard, site_summary

DEMO_FILE = "sample_data/fecon_all_charts_history.csv"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
TABS = ["📊 Dashboard", "🏆 Summary", "➕ Add month", "✏️ Fix data", "⚙️ Style"]
NAME_STYLES = {"callout": "Box + line", "box": "Box at end", "text": "Text at end"}

st.set_page_config(page_title="Competitor Trend Charts", page_icon="📈", layout="wide")
st.markdown("""<style>
    .block-container {padding-top: 2.2rem; padding-bottom: 3rem;}
    [data-testid="stMetricValue"] {font-size: 1.9rem;}
    [data-testid="stSidebar"] h1 {font-size: 1.5rem;}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Remembered state
# ---------------------------------------------------------------------------
# histories : {chart name: table} as loaded / after "Add month"
# edits     : {chart name: table} typed corrections from "Fix data"
# version   : changes when `histories` is replaced -> the data table starts fresh
# axis      : {chart name: (top, step)} for charts with a manual y-axis
# saved     : False when there are changes the user hasn't downloaded yet
# flash     : a message to show once after a button did something
# uploads   : counter used to empty the upload boxes after a successful upload

defaults = {"histories": {}, "edits": {}, "version": 0, "axis": {}, "saved": True, "flash": None,
            "uploads": 0, "load_errors": [], "add_errors": [], "known_names": [],
            "editor_key": None, "editor_base": None}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
state = st.session_state


def current_histories():
    """Loaded data with any typed corrections applied."""
    return {**state.histories, **state.edits}


def set_histories(new_histories, saved):
    state.histories = new_histories
    state.edits = {}
    state.version += 1
    state.saved = saved


def all_competitors(histories):
    """Every competitor name in any chart, in first-seen order."""
    names = []
    for history in histories.values():
        names += [n for n in history.columns if n not in names]
    return names


def guess_month_from_filename(filename):
    """ 'fecon_red_line_aug_2026.csv' -> 'Aug 2026' (or None) """
    match = re.search(r"(" + "|".join(MONTHS) + r")[a-z]*[_\-\s]*(20\d\d)", filename.lower())
    return f"{match.group(1).title()} {match.group(2)}" if match else None


def next_month(histories):
    periods = [p for h in histories.values() for p in h.index]
    if not periods:
        return pd.Timestamp.today().strftime("%b %Y")
    last = pd.to_datetime(max(periods), format="%Y-%m")
    return (last + pd.DateOffset(months=1)).strftime("%b %Y")


def safe_file_name(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "chart"


def go_to(tab, message=None):
    state.tab = tab
    state.flash = message


# --- Button callbacks (run before the page is redrawn) -----------------------

def open_data_file(upload_key):
    file = state.get(upload_key)
    if file is None:
        return
    try:
        histories = load_histories(file, default_metric=Path(file.name).stem)
    except DataError as e:
        state.load_errors = e.messages
        return
    state.load_errors = []
    set_histories(histories, saved=True)
    state.uploads += 1  # empties the upload box
    go_to(TABS[0], f"Opened {file.name}: {len(histories)} charts")


def open_demo():
    set_histories(load_histories(DEMO_FILE), saved=True)
    go_to(TABS[0], "Demo data loaded - have a look around!")


def add_month_clicked(month_data, month_text, replace):
    try:
        updated = add_month_all(current_histories(), month_text, month_data, replace=replace)
    except DataError as e:
        state.add_errors = e.messages
        return
    except ValueError as e:  # month text not understood
        state.add_errors = [str(e)]
        return
    state.add_errors = []
    set_histories(updated, saved=False)
    state.uploads += 1
    go_to(TABS[0], f"{month_text} added to {len(month_data.columns)} charts. Remember to save your data file.")


def mark_saved():
    state.saved = True


def start_over():
    for key in list(state.keys()):
        del state[key]


# ---------------------------------------------------------------------------
# Sidebar: the data file
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📈 Trend Charts")
    st.caption("Monthly SEO competitor charts")

    histories = current_histories()
    if histories:
        all_periods = sorted({p for h in histories.values() for p in h.index})
        with st.container(border=True):
            st.markdown("**📁 Your data**")
            st.markdown(f"**{len(histories)}** charts · **{len(all_competitors(histories))}** competitors  \n"
                        f"{period_label(all_periods[0])} – {period_label(all_periods[-1])}")
            save_slot = st.container()  # filled at the end, once all edits are known
    else:
        st.info("No data yet. Open your data file, or try the demo.")
        save_slot = None

    upload_key = f"history_upload_{state.uploads}"
    st.file_uploader("Open data file", type="csv", key=upload_key, on_change=open_data_file, args=(upload_key,),
                     help="The CSV you saved last month (it holds every chart).")
    for message in state.load_errors:
        st.error(message)
    st.button("✨ Try demo data", on_click=open_demo, width="stretch")

    with st.expander("How it works"):
        st.markdown("1. **Open** last month's data file (first time: skip)\n"
                    "2. **➕ Add month**: upload the new Semrush export\n"
                    "3. **📊 Dashboard**: check and download the charts\n"
                    "4. **💾 Save** the data file for next month")
    if histories:
        st.button("Start over", on_click=start_over, type="tertiary")

if state.flash:
    st.toast(state.flash, icon="✅")
    state.flash = None

tabs = st.tabs(TABS, key="tab", on_change="rerun")
tab_dashboard, tab_summary, tab_add, tab_fix, tab_style = tabs


# ---------------------------------------------------------------------------
# ➕ Add month   (filled first: it can change the data everything else shows)
# ---------------------------------------------------------------------------

with tab_add:
    st.subheader("Add this month's numbers")
    st.caption("One Semrush export updates every chart at once.")

    with st.container(border=True):
        st.markdown("**① Upload the Semrush competitor export**")
        semrush_file = st.file_uploader("Semrush export (CSV)", type="csv", key=f"semrush_{state.uploads}",
                                        label_visibility="collapsed")

    month_data = None
    if semrush_file is not None:
        try:
            month_data = load_semrush_month(semrush_file)
        except DataError as e:
            for message in e.messages:
                st.error(message)

    if month_data is not None:
        with st.container(border=True):
            st.markdown("**② Check the month**")
            c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
            month_text = c1.text_input("Month", guess_month_from_filename(semrush_file.name)
                                       or next_month(state.histories), help="e.g. Sep 2026")
            replace = c2.checkbox("This month is already there - replace it")

            st.caption(f"Found **{len(month_data)} competitors** and **{len(month_data.columns)} charts**: "
                       + ", ".join(month_data.columns))
            with st.expander("See the numbers"):
                st.dataframe(month_data, width="stretch")

            known = all_competitors(state.histories)
            if known:
                new_names = [n for n in month_data.index if n not in known]
                missing = [n for n in known if n not in month_data.index]
                if new_names:
                    st.warning("**New names** (they'll get their own line): " + ", ".join(new_names)
                               + "  \nIf one is just spelled differently, fix it in ✏️ Fix data → Rename.")
                if missing:
                    st.info("**Not in this file** (empty this month): " + ", ".join(missing))

        with st.container(border=True):
            st.markdown("**③ Add it**")
            st.button(f"Add {month_text} to all {len(month_data.columns)} charts", type="primary",
                      on_click=add_month_clicked, args=(month_data, month_text, replace))
            for message in state.add_errors:
                st.error(message)


# ---------------------------------------------------------------------------
# No data yet: a friendly start screen
# ---------------------------------------------------------------------------

if not state.histories:
    with tab_dashboard:
        st.header("👋 Welcome")
        st.markdown("Turn your monthly Semrush exports into clean competitor charts - no editing needed.")
        c1, c2, c3 = st.columns(3)
        with c1.container(border=True, height="stretch"):
            st.markdown("#### 🆕 First time?")
            st.markdown("Open the **➕ Add month** tab and upload your Semrush competitor export.")
        with c2.container(border=True, height="stretch"):
            st.markdown("#### 📅 Every month")
            st.markdown("Open **last month's data file** in the sidebar, then add the new month.")
        with c3.container(border=True, height="stretch"):
            st.markdown("#### 👀 Just looking?")
            st.markdown("Load example data to see how it works.")
            st.button("✨ Try demo data", on_click=open_demo, type="primary", key="demo_main")
    for tab in (tab_summary, tab_fix, tab_style):
        tab.info("No data yet - start in 📊 Dashboard.")
    st.stop()


# ---------------------------------------------------------------------------
# 📊 Dashboard, part 1: which chart (other tabs need to know)
# ---------------------------------------------------------------------------

chart_names = list(current_histories())
if state.get("metric") not in chart_names:
    state.metric = chart_names[0]

with tab_dashboard:
    metric = st.pills("Chart", chart_names, key="metric", required=True, label_visibility="collapsed")
    dashboard_body = st.container()  # filled after Fix data and Style


# ---------------------------------------------------------------------------
# ✏️ Fix data
# ---------------------------------------------------------------------------

with tab_fix:
    st.subheader("Fix numbers")
    if state.get("fix_metric") not in chart_names:
        state.fix_metric = metric
    fix_metric = st.segmented_control("Chart to fix", chart_names, key="fix_metric", required=True)
    st.caption("Click a cell to change it. Leave it empty if there's no data that month. "
               "Use **+** below the table to add a month.")

    # The table must start from the same data while it's on screen, otherwise
    # Streamlit applies your typing twice. So we keep a snapshot per chart.
    editor_key = f"editor_{state.version}_{fix_metric}"
    if state.editor_key != editor_key:
        state.editor_key = editor_key
        state.editor_base = current_histories()[fix_metric].reset_index()
    edited = st.data_editor(
        state.editor_base, num_rows="dynamic", hide_index=True, width="stretch", key=editor_key,
        column_config={"period": st.column_config.TextColumn("Month", help="e.g. 2026-09 or Sep 26")},
    )
    try:
        fixed = load_history(io.BytesIO(edited.to_csv(index=False).encode("utf-8")), first_row=1)
        if not fixed.equals(state.edits.get(fix_metric, state.histories[fix_metric])):
            state.saved = False
        state.edits[fix_metric] = fixed
    except DataError as e:
        st.error("Please fix these cells:\n\n" + "\n".join(f"- {m}" for m in e.messages))

    with st.expander("Rename or add a competitor (all charts)"):
        st.caption("Rename when Semrush spells a name differently, e.g. *Diamond Mowers* → *Diamond Mower*.")
        names_now = all_competitors(current_histories())
        c1, c2 = st.columns(2)
        with c1:
            old = st.selectbox("Rename", names_now)
            renamed = st.text_input("New name").strip()
            if st.button("Rename", disabled=not renamed):
                if renamed in names_now:
                    st.warning("That name is already used.")
                else:
                    set_histories({m: h.rename(columns={old: renamed}) for m, h in current_histories().items()},
                                  saved=False)
                    st.rerun()
        with c2:
            new_name = st.text_input("Add competitor").strip()
            if st.button("Add", disabled=not new_name):
                if new_name in names_now:
                    st.warning("That competitor already exists.")
                else:
                    set_histories({m: h.assign(**{new_name: float("nan")}) for m, h in current_histories().items()},
                                  saved=False)
                    st.rerun()


# ---------------------------------------------------------------------------
# ⚙️ Style
# ---------------------------------------------------------------------------

histories = current_histories()
history = histories[metric]
names = all_competitors(histories)

# Keep the "shown" list up to date when new competitors appear.
if "visible" not in state:
    state.visible = list(names)
else:
    newcomers = [n for n in names if n not in state.known_names]
    state.visible = [n for n in state.visible if n in names] + newcomers
state.known_names = list(names)
state.setdefault("show_values", True)
state.setdefault("name_style", "callout")

with tab_style:
    st.subheader("Style")
    st.caption("These settings apply to every chart.")
    with st.container(border=True):
        visible = st.multiselect("Competitors to show", names, key="visible",
                                 help="Hiding a competitor keeps its data - it's just not drawn.")
        site_options = ["(none)"] + visible
        if state.get("our_site") not in site_options:
            state.our_site = "Fecon" if "Fecon" in site_options else "(none)"
        c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
        our_site = c1.selectbox("Our site", site_options, key="our_site",
                                help="Drawn as a thicker line on top, and used for the dashboard tiles.")
        name_style = c2.segmented_control("Competitor names", list(NAME_STYLES), key="name_style",
                                          format_func=NAME_STYLES.get, required=True)
        show_values = c3.toggle("Show numbers", key="show_values")

    with st.expander("🎨 Colors"):
        st.caption("Known competitors keep fixed colors (Fecon is always red). Changes here last until you "
                   "close the page.")
        default_colors = pick_colors(names)
        picker_columns = st.columns(4)
        colors = {n: picker_columns[i % 4].color_picker(n, default_colors[n], key=f"color_{n}")
                  for i, n in enumerate(visible)}

    shown_here = [n for n in visible if n in history.columns and history[n].notna().any()]
    max_value = float(history[shown_here].max().max()) if shown_here else 0.0
    auto_top, auto_step = auto_axis(max_value) if shown_here else (0, 0)

    with st.expander(f"📏 Y-axis for {metric}"):
        st.caption(f"Automatic: 0 to {auto_top:,.0f} in steps of {auto_step:,.0f}.")
        manual = st.toggle("Set it myself", value=metric in state.axis, key=f"manual_{metric}")
        if manual and shown_here:
            saved_top, saved_step = state.axis.get(metric, (auto_top, auto_step))
            state.setdefault(f"ymax_{metric}", float(saved_top))
            state.setdefault(f"ystep_{metric}", float(saved_step))
            a1, a2 = st.columns(2)
            y_max = a1.number_input("Top", min_value=1.0, step=float(auto_step), format="%g", key=f"ymax_{metric}")
            y_step = a2.number_input("Step (e.g. 2000 = 2K)", min_value=0.1, step=float(auto_step),
                                     format="%g", key=f"ystep_{metric}")
            state.axis[metric] = (y_max, y_step)
            if max_value > y_max:
                def expand():
                    state[f"ymax_{metric}"] = float(-(-max_value // y_step) * y_step)

                st.warning(f"The highest value ({max_value:,.0f}) is above {y_max:,.0f}, so it would be cut off.")
                st.button("Make it fit", on_click=expand)
        else:
            state.axis.pop(metric, None)

site = None if our_site == "(none)" else our_site


def settings_for(chart_name, file_format="png"):
    """The same look for every chart; only the y-axis is per chart."""
    y_max, y_step = state.axis.get(chart_name, (None, None))
    return ChartSettings(hidden=[n for n in names if n not in visible], colors=colors, show_values=show_values,
                         name_style=name_style, highlight=site, y_max=y_max, y_step=y_step,
                         file_format=file_format)


@st.cache_data(show_spinner="Drawing chart...")
def make_chart(history, settings):
    """Remember finished charts so unchanged settings don't redraw."""
    return render_chart(history, settings)


# ---------------------------------------------------------------------------
# 📊 Dashboard, part 2
# ---------------------------------------------------------------------------

with dashboard_body:
    if not shown_here:
        st.warning("None of the shown competitors has data in this chart. Check ⚙️ Style.")
    else:
        last, previous = latest_months(history)
        board = leaderboard(history, shown_here)
        mine = site_summary(history, shown_here, site) if site else None
        mover = biggest_mover(board)
        leader = board.iloc[0]
        compare = f"vs {period_label(previous)}" if previous else "first month"

        # --- KPI tiles ---------------------------------------------------------
        k1, k2, k3, k4 = st.columns(4)
        TILE = 190  # all four tiles the same height (only the first has a trend line)
        if mine:
            k1.metric(f"{site} · {period_label(last)}", fmt(mine["value"]),
                      fmt_change(mine["change"], mine["change_pct"]), border=True, height=TILE,
                      chart_data=mine["trend"], chart_type="area",
                      help=f"{site}'s {metric}, {compare}")
            move = mine["rank_move"]
            k2.metric("Rank", f"#{mine['rank']} of {mine['of']}",
                      None if not move else f"{move:+d} place{'s' if abs(move) > 1 else ''}", border=True, height=TILE,
                      help=f"{site}'s position among the competitors shown, {compare}")
        elif site:
            k1.metric(f"{site} · {period_label(last)}", "No data", border=True, height=TILE,
                      help=f"{site} has no {metric} number for {period_label(last)}.")
            k2.metric("Competitors", len(board), border=True, height=TILE)
        else:
            k1.metric(f"Total · {period_label(last)}", fmt(board["Value"].sum()), border=True, height=TILE,
                      help="Pick 'Our site' in ⚙️ Style to see your own numbers here.")
            k2.metric("Competitors", len(board), border=True, height=TILE)
        k3.metric("🏆 Leader", str(leader["Competitor"]), fmt(leader["Value"]), delta_color="off",
                  delta_arrow="off", border=True, height=TILE, help=f"Highest {metric} in {period_label(last)}")
        if mover is not None:
            k4.metric("🚀 Biggest move", str(mover["Competitor"]), fmt_change(mover["Change"], mover["Change %"]),
                      border=True, height=TILE, help=f"Largest change {compare}")
        else:
            k4.metric("🚀 Biggest move", "–", border=True, height=TILE, help="Needs two months of data")

        # --- The chart ----------------------------------------------------------
        try:
            png = make_chart(history, settings_for(metric))
        except ValueError as e:  # e.g. an axis step that is far too small
            st.error(str(e))
            st.stop()
        with st.container(border=True):
            st.image(png, width="stretch")
            if len(history) < 2:
                st.caption("Only one month so far - the lines appear once the next month is added.")

        # --- Downloads ----------------------------------------------------------
        # The ZIP and SVG are only built when clicked, in a background thread that
        # CAN'T read st.session_state - so everything they need is prepared now.
        file_end = f"{history.index[0]}_to_{history.index[-1]}"
        zip_jobs = [(f"{safe_file_name(m)}_{file_end}.png", h, settings_for(m))
                    for m, h in histories.items() if any(n in h.columns for n in visible)]
        svg_settings = settings_for(metric, "svg")

        def all_charts_zip():
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for zip_name, chart_history, chart_settings in zip_jobs:
                    try:
                        archive.writestr(zip_name, render_chart(chart_history, chart_settings))
                    except ValueError:
                        continue
            return buffer.getvalue()

        chart_file = f"{safe_file_name(metric)}_{file_end}"
        with st.container(horizontal=True):
            st.download_button("⬇ Download this chart", png, f"{chart_file}.png", "image/png",
                               type="primary", on_click="ignore", help="PNG, 2727 × 1087 pixels")
            every_month = sorted({p for h in histories.values() for p in h.index})
            st.download_button(f"⬇ All {len(zip_jobs)} charts (ZIP)", all_charts_zip,
                               f"charts_{every_month[0]}_to_{every_month[-1]}.zip", "application/zip",
                               on_click="ignore")
            st.download_button("SVG", lambda: render_chart(history, svg_settings), f"{chart_file}.svg",
                               "image/svg+xml", on_click="ignore", type="tertiary",
                               help="Vector file for designers")

        # --- Leaderboard ----------------------------------------------------------
        st.markdown(f"#### 🏅 {metric} · {period_label(last)}")
        table = board.copy()
        table["Competitor"] = [("⭐ " if n == site else "") + n for n in table["Competitor"]]
        table["Change"] = [fmt_change(c, p) or "–" for c, p in zip(board["Change"], board["Change %"])]
        is_da = metric.strip().upper() == "DA"
        st.dataframe(
            table, hide_index=True, width="stretch",
            column_order=["Rank", "Competitor", "Value", "Change"] + ([] if is_da else ["Share"]) + ["Trend"],
            column_config={
                "Rank": st.column_config.NumberColumn("#", width="small"),
                "Value": st.column_config.NumberColumn(metric, format="localized"),
                "Change": st.column_config.TextColumn(f"Change {compare}"),
                "Share": st.column_config.ProgressColumn("Share of total", format="percent",
                                                         min_value=0.0, max_value=1.0),
                "Trend": st.column_config.LineChartColumn("Trend"),
            },
        )


# ---------------------------------------------------------------------------
# 🏆 Summary: our site across every chart
# ---------------------------------------------------------------------------

with tab_summary:
    if not site:
        st.info("Choose **Our site** in ⚙️ Style to see how it does across all charts.")
    else:
        st.subheader(f"{site} across all charts")
        rows = []
        cards = st.columns(4)
        for i, (chart_name, chart_history) in enumerate(histories.items()):
            chart_names_shown = [n for n in visible if n in chart_history.columns]
            info = site_summary(chart_history, chart_names_shown, site)
            if info is None:
                continue
            last_here, _ = latest_months(chart_history)
            cards[i % 4].metric(
                chart_name, fmt(info["value"]), fmt_change(info["change"], info["change_pct"]), border=True,
                chart_data=info["trend"], chart_type="area",
                help=f"Rank #{info['rank']} of {info['of']} in {period_label(last_here)}",
            )
            rows.append({"Chart": chart_name, "Month": period_label(last_here), "Value": info["value"],
                         "Change vs month before": fmt_change(info["change"], info["change_pct"]) or "–",
                         "Rank": f"#{info['rank']} of {info['of']}", "Trend": info["trend"]})
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
                "Value": st.column_config.NumberColumn(format="localized"),
                "Trend": st.column_config.LineChartColumn(),
            })
        else:
            st.info(f"No numbers for {site} yet.")


# ---------------------------------------------------------------------------
# Sidebar: save button (last, so it includes every correction made above)
# ---------------------------------------------------------------------------

if save_slot is not None:
    with save_slot:
        if not state.saved:
            st.warning("Unsaved changes", icon="⚠️")
        st.download_button("💾 Save data file", histories_to_csv(histories),
                           f"trend_data_{max(p for h in histories.values() for p in h.index)}.csv", "text/csv",
                           type="primary" if not state.saved else "secondary", width="stretch",
                           on_click=mark_saved, help="Keep this file - open it next month to continue.")
