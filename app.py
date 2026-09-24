"""
app.py - the web page. Run it with:

    streamlit run app.py

How Streamlit works (the one thing to know):
  Every time the user clicks or types anything, Streamlit runs this WHOLE
  file again from top to bottom. Values that must survive between runs are
  kept in `st.session_state` (a dictionary that Streamlit remembers).

The team makes one chart per metric (DA, Worldwide Traffic, US Traffic,
Top 3 Volume, ...). All metrics live in ONE history file, and one Semrush
upload adds the new month to all of them.

Page layout:
  1. Load history     - upload the history CSV (or try a sample)
  2. Add a month      - upload this month's Semrush export
  3. Choose a chart   - pick the metric and check / edit its data
  4. Chart            - options, preview, downloads (one chart or all as ZIP)
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

SAMPLES = {
    "Fecon - all charts (US Traffic + Top 100)": "sample_data/fecon_all_charts_history.csv",
}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

st.set_page_config(page_title="Competitor Trend Chart", layout="wide")
st.title("Competitor Trend Chart")


# ---------------------------------------------------------------------------
# Remembered state
# ---------------------------------------------------------------------------
# histories   : {metric: table} as loaded / after "Add month"
# edits       : {metric: table} typed changes from the data table, kept per chart
# version     : changes whenever `histories` is replaced -> the table editor starts fresh
# axis        : {metric: (top, step)} for charts with a manual y-axis
# loaded_file : the uploaded history file we already read

defaults = {"histories": {}, "edits": {}, "version": 0, "axis": {},
            "loaded_file": None, "editor_key": None, "editor_base": None}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)
state = st.session_state


def current_histories():
    """Loaded data with any typed changes applied."""
    return {**state.histories, **state.edits}


def set_histories(new_histories):
    state.histories = new_histories
    state.edits = {}
    state.version += 1


def show_errors(error):
    st.error("Please fix these problems:\n\n" + "\n".join(f"- {m}" for m in error.messages))


def guess_month_from_filename(filename):
    """ 'fecon_red_line_aug_2026.csv' -> 'Aug 2026' (or None) """
    match = re.search(r"(" + "|".join(MONTHS) + r")[a-z]*[_\-\s]*(20\d\d)", filename.lower())
    if match:
        return f"{match.group(1).title()} {match.group(2)}"
    return None


def next_month(histories):
    """The month after the latest month in any chart."""
    periods = [p for h in histories.values() for p in h.index]
    if not periods:
        return pd.Timestamp.today().strftime("%b %Y")
    last = pd.to_datetime(max(periods), format="%Y-%m")
    return (last + pd.DateOffset(months=1)).strftime("%b %Y")


def all_competitors(histories):
    """Every competitor name in any chart, in first-seen order."""
    names = []
    for history in histories.values():
        names += [n for n in history.columns if n not in names]
    return names


def safe_file_name(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "chart"


# ---------------------------------------------------------------------------
# 1. Load history
# ---------------------------------------------------------------------------

st.header("1. Load history")
st.caption("One CSV holds every chart: columns `metric, period, Fecon, Virnig, ...` "
           "(e.g. `US Traffic, 2026-01, 16487, 11431`). Download the updated file at the bottom "
           "and upload it again next month. First time? Skip this and upload a Semrush export below.")

col_upload, col_sample = st.columns([2, 1])
with col_upload:
    history_file = st.file_uploader("History CSV", type="csv", key="history_upload")
with col_sample:
    sample = st.selectbox("...or try a sample", ["(none)"] + list(SAMPLES))
    if st.button("Load sample", disabled=sample == "(none)"):
        set_histories(load_histories(SAMPLES[sample]))
        state.loaded_file = None

# Read a newly uploaded history file once.
if history_file is not None and state.loaded_file != history_file.file_id:
    state.loaded_file = history_file.file_id
    try:
        # An old single-chart file (no metric column) is named after the file.
        set_histories(load_histories(history_file, default_metric=Path(history_file.name).stem))
    except DataError as e:
        show_errors(e)


# ---------------------------------------------------------------------------
# 2. Add a month from a Semrush export
# ---------------------------------------------------------------------------

st.header("2. Add a month")
semrush_file = st.file_uploader("Semrush competitor export for ONE month", type="csv", key="semrush_upload")

if semrush_file is not None:
    try:
        month_data = load_semrush_month(semrush_file)
    except DataError as e:
        show_errors(e)
        month_data = None

    if month_data is not None:
        c1, c2 = st.columns(2)
        month_text = c1.text_input("Month", guess_month_from_filename(semrush_file.name)
                                   or next_month(state.histories))
        replace = c2.checkbox("Replace this month if it already exists")

        st.caption(f"This file has {len(month_data.columns)} metrics - each one becomes a chart:")
        st.dataframe(month_data, width="stretch")

        # Warn about names that don't match the history - usually a spelling difference
        # like "Diamond Mowers" vs "Diamond Mower", which would create two separate lines.
        known = all_competitors(state.histories)
        if known:
            new_names = [n for n in month_data.index if n not in known]
            missing = [n for n in known if n not in month_data.index]
            if new_names:
                st.warning("Not in the history yet (a new line will be added): " + ", ".join(new_names))
            if missing:
                st.info("In the history but not in this file (this month will be empty): " + ", ".join(missing))

        if st.button(f"Add {month_text} to all {len(month_data.columns)} charts", type="primary"):
            try:
                set_histories(add_month_all(current_histories(), month_text, month_data, replace=replace))
                st.success(f"Added {month_text}.")
            except DataError as e:
                show_errors(e)
            except ValueError as e:  # month text not understood
                show_errors(DataError([str(e)]))


# ---------------------------------------------------------------------------
# 3. Choose a chart and check its data
# ---------------------------------------------------------------------------

if not state.histories:
    st.info("Load a history CSV, a sample, or a Semrush export to start.")
    st.stop()  # nothing more to show yet

st.header("3. Choose a chart")
metric = st.selectbox("Chart", list(current_histories()), key="metric")

st.caption("Check the numbers for this chart. Type to correct a value, leave a cell empty for a "
           "missing month, use the + at the bottom to add a month.")

# The table editor must always start from the same data while it is on screen,
# otherwise Streamlit applies your typed changes twice. So we take a snapshot
# when the chart changes (or new data is loaded) and keep using it.
editor_key = f"editor_{state.version}_{metric}"
if state.editor_key != editor_key:
    state.editor_key = editor_key
    state.editor_base = current_histories()[metric].reset_index()

edited = st.data_editor(
    state.editor_base,
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    key=editor_key,
    column_config={"period": st.column_config.TextColumn("period", help="e.g. 2026-09 or Sep 26")},
)

# Check the edited table with the SAME rules as a CSV upload.
try:
    history = load_history(io.BytesIO(edited.to_csv(index=False).encode("utf-8")), first_row=1)
    state.edits[metric] = history
except DataError as e:
    show_errors(e)
    st.stop()

with st.expander("Add or rename a competitor (applies to all charts)"):
    c1, c2 = st.columns(2)
    names = all_competitors(current_histories())
    new_name = c1.text_input("New competitor name").strip()
    if c1.button("Add competitor", disabled=not new_name):
        if new_name in names:
            st.warning("That competitor already exists.")
        else:
            set_histories({m: h.assign(**{new_name: float("nan")}) for m, h in current_histories().items()})
            st.rerun()
    old = c2.selectbox("Rename", names)
    renamed = c2.text_input("New name for it").strip()
    if c2.button("Rename", disabled=not renamed):
        if renamed in names:
            st.warning("That name is already used. Rename can't merge two competitors.")
        else:
            set_histories({m: h.rename(columns={old: renamed}) for m, h in current_histories().items()})
            st.rerun()


# ---------------------------------------------------------------------------
# 4. Chart
# ---------------------------------------------------------------------------

st.header(f"4. Chart: {metric}")
histories = current_histories()
names = all_competitors(histories)

c1, c2, c3 = st.columns([3, 1, 1])
visible = c1.multiselect("Competitors to show (all charts)", names, default=names,
                         help="Hiding a competitor keeps its data - it's just not drawn.")
show_values = c2.checkbox("Show values", value=True)
NAME_STYLES = {"callout": "Box + line (Manus style)", "box": "Box at line end", "text": "Text at line end"}
name_style = c3.selectbox("Competitor names", list(NAME_STYLES), format_func=NAME_STYLES.get)

options = ["(none)"] + visible
highlight = st.selectbox("Our site (thicker line, drawn on top)", options,
                         index=options.index("Fecon") if "Fecon" in options else 0)

default_colors = pick_colors(names)
with st.expander("Colors"):
    st.caption("Known competitors have fixed colors (Fecon is always red). Changes here last until "
               "you close the page - ask to add a color to DEFAULT_COLORS in chart.py to make it permanent.")
    picker_columns = st.columns(4)
    colors = {}
    for i, name in enumerate(visible):
        colors[name] = picker_columns[i % 4].color_picker(name, default_colors[name], key=f"color_{name}")

# --- Y-axis for THIS chart (each chart has its own scale) ---------------------
shown_here = [n for n in visible if n in history.columns and history[n].notna().any()]
if not shown_here:
    st.warning("None of the selected competitors has data in this chart.")
    st.stop()
max_value = float(history[shown_here].max().max())
auto_top, auto_step = auto_axis(max_value)

with st.expander(f"Y-axis for {metric} (automatic: 0 to {auto_top:,.0f} in steps of {auto_step:,.0f})"):
    manual = st.toggle("Set the axis myself", value=metric in state.axis, key=f"manual_{metric}")
    if manual:
        # Start from the saved or automatic values when the boxes appear.
        saved_top, saved_step = state.axis.get(metric, (auto_top, auto_step))
        st.session_state.setdefault(f"ymax_{metric}", float(saved_top))
        st.session_state.setdefault(f"ystep_{metric}", float(saved_step))
        a1, a2 = st.columns(2)
        y_max = a1.number_input("Top of axis", min_value=1.0, step=float(auto_step),
                                format="%g", key=f"ymax_{metric}")
        y_step = a2.number_input("Step (e.g. 2000 for 2K)", min_value=0.1,
                                 step=float(auto_step), format="%g", key=f"ystep_{metric}")
        state.axis[metric] = (y_max, y_step)

        if max_value > y_max:
            def expand():
                # Round up to the next whole step above the highest value.
                st.session_state[f"ymax_{metric}"] = float(-(-max_value // y_step) * y_step)

            st.warning(f"The highest value ({max_value:,.0f}) is above the top of the axis "
                       f"({y_max:,.0f}), so part of the chart will be cut off.")
            st.button("Expand axis to fit", on_click=expand)
    else:
        state.axis.pop(metric, None)


def settings_for(chart_metric, file_format="png"):
    """The same options for every chart; only the y-axis is per chart."""
    y_max, y_step = state.axis.get(chart_metric, (None, None))
    return ChartSettings(
        hidden=[n for n in names if n not in visible],
        colors=colors,
        show_values=show_values,
        name_style=name_style,
        highlight=None if highlight == "(none)" else highlight,
        y_max=y_max,
        y_step=y_step,
        file_format=file_format,
    )


@st.cache_data(show_spinner="Drawing chart...")
def make_chart(history, settings):
    """Remember finished charts so unchanged settings don't redraw."""
    return render_chart(history, settings)


try:
    png = make_chart(history, settings_for(metric))
except ValueError as e:  # e.g. an axis step that is far too small
    st.error(str(e))
    st.stop()
st.image(png, width="stretch")
if len(history) < 2:
    st.info("This chart has only one month so far - the lines appear once a second month is added.")

# --- Downloads -------------------------------------------------------------
all_periods = sorted({p for h in histories.values() for p in h.index})
default_name = f"{all_periods[0]}_to_{all_periods[-1]}"
file_name = safe_file_name(st.text_input("File name ending", default_name))


def all_charts_zip():
    """Runs only when the ZIP button is clicked: every chart as a PNG in one file."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for chart_metric, chart_history in histories.items():
            if not any(n in chart_history.columns for n in visible):
                continue
            try:
                image = make_chart(chart_history, settings_for(chart_metric))
            except ValueError:
                continue  # e.g. nothing to draw in this chart
            archive.writestr(f"{safe_file_name(chart_metric)}_{file_name}.png", image)
    return buffer.getvalue()


chart_file = f"{safe_file_name(metric)}_{file_name}"
d1, d2, d3, d4 = st.columns(4)
d1.download_button(f"PNG: {metric}", png, f"{chart_file}.png", "image/png", type="primary")
d2.download_button(f"SVG: {metric}", lambda: make_chart(history, settings_for(metric, "svg")),
                   f"{chart_file}.svg", "image/svg+xml")
d3.download_button(f"All {len(histories)} charts (ZIP of PNGs)", all_charts_zip,
                   f"charts_{file_name}.zip", "application/zip")
d4.download_button("Updated history CSV", histories_to_csv(histories),
                   f"history_{file_name}.csv", "text/csv",
                   help="Keep this file - upload it next month and add the new month to it.")

st.caption(f"{len(histories)} charts · this chart: {len(history)} months "
           f"({period_label(history.index[0])} - {period_label(history.index[-1])}), "
           f"{len(shown_here)} competitors shown.")
