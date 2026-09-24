"""
app.py - the web page. Run it with:

    streamlit run app.py

How Streamlit works (the one thing to know):
  Every time the user clicks or types anything, Streamlit runs this WHOLE
  file again from top to bottom. Values that must survive between runs are
  kept in `st.session_state` (a dictionary that Streamlit remembers).

Page layout:
  1. Load history     - upload a history CSV (or try a sample)
  2. Add a month      - upload a Semrush export, pick the metric and month
  3. Check the data   - editable table
  4. Chart            - show/hide competitors, options, preview, downloads
"""

import io
import re

import pandas as pd
import streamlit as st

from chart import ChartSettings, auto_axis, pick_colors, render_chart
from data_loader import (
    DataError,
    add_month,
    history_to_csv,
    load_history,
    load_semrush_month,
    period_label,
)

SAMPLES = {
    "Fecon - Top 100 keywords": "sample_data/fecon_top100_history.csv",
    "Fecon - Monthly traffic": "sample_data/fecon_traffic_history.csv",
}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

st.set_page_config(page_title="Competitor Trend Chart", layout="wide")
st.title("Competitor Trend Chart")


# ---------------------------------------------------------------------------
# Remembered state
# ---------------------------------------------------------------------------
# "history"        : the table the editor starts from
# "editor_version" : changed whenever "history" is replaced, so the table
#                    editor starts fresh instead of keeping old edits
# "loaded_file"    : which uploaded file we already read (so we don't re-read it every run)

if "history" not in st.session_state:
    st.session_state.history = None
    st.session_state.editor_version = 0
    st.session_state.loaded_file = None


def set_history(new_history):
    st.session_state.history = new_history
    st.session_state.editor_version += 1


def show_errors(error):
    st.error("Please fix these problems:\n\n" + "\n".join(f"- {m}" for m in error.messages))


def guess_month_from_filename(filename):
    """ 'fecon_red_line_aug_2026.csv' -> 'Aug 2026' (or None) """
    match = re.search(r"(" + "|".join(MONTHS) + r")[a-z]*[_\-\s]*(20\d\d)", filename.lower())
    if match:
        return f"{match.group(1).title()} {match.group(2)}"
    return None


def next_month(history):
    """The month after the last one in the history."""
    if history is None or history.empty:
        return pd.Timestamp.today().strftime("%b %Y")
    last = pd.to_datetime(history.index[-1], format="%Y-%m")
    return (last + pd.DateOffset(months=1)).strftime("%b %Y")


# ---------------------------------------------------------------------------
# 1. Load history
# ---------------------------------------------------------------------------

st.header("1. Load history")
st.caption("A history CSV has one row per month and one column per competitor, "
           "e.g. `period,Fecon,Virnig` then `2026-01,3369,5710`. "
           "Download the updated file at the bottom of the page and upload it again next month.")

col_upload, col_sample = st.columns([2, 1])
with col_upload:
    history_file = st.file_uploader("History CSV", type="csv", key="history_upload")
with col_sample:
    sample = st.selectbox("...or try a sample", ["(none)"] + list(SAMPLES))
    if st.button("Load sample", disabled=sample == "(none)"):
        set_history(load_history(SAMPLES[sample]))
        st.session_state.loaded_file = None

# Read a newly uploaded history file once.
if history_file is not None and st.session_state.loaded_file != history_file.file_id:
    st.session_state.loaded_file = history_file.file_id
    try:
        set_history(load_history(history_file))
    except DataError as e:
        show_errors(e)


# ---------------------------------------------------------------------------
# 2. Add a month from a Semrush export
# ---------------------------------------------------------------------------

st.header("2. Add a month (optional)")
semrush_file = st.file_uploader("Semrush competitor export for ONE month", type="csv", key="semrush_upload")

if semrush_file is not None:
    try:
        month_data = load_semrush_month(semrush_file)
    except DataError as e:
        show_errors(e)
        month_data = None

    if month_data is not None:
        metrics = list(month_data.columns)
        c1, c2, c3 = st.columns(3)
        metric = c1.selectbox("Metric to chart", metrics,
                              index=metrics.index("Top 100") if "Top 100" in metrics else 0)
        month_text = c2.text_input("Month", guess_month_from_filename(semrush_file.name)
                                   or next_month(st.session_state.history))
        replace = c3.checkbox("Replace this month if it already exists")

        st.dataframe(month_data[[metric]], width="content")

        # Warn about names that don't match the history - usually a spelling difference
        # like "Diamond Mowers" vs "Diamond Mower", which would create two separate lines.
        history = st.session_state.history
        if history is not None:
            new_names = [n for n in month_data.index if n not in history.columns]
            missing = [n for n in history.columns if n not in month_data.index]
            if new_names:
                st.warning("Not in the history yet (a new line will be added): " + ", ".join(new_names))
            if missing:
                st.info("In the history but not in this file (this month will be empty): " + ", ".join(missing))

        if st.button(f"Add '{metric}' as {month_text}", type="primary"):
            try:
                base = st.session_state.get("edited_history", history)
                set_history(add_month(base, month_text, month_data[metric], replace=replace))
                st.success(f"Added {month_text}.")
            except (DataError, ValueError) as e:
                show_errors(e if isinstance(e, DataError) else DataError([str(e)]))


# ---------------------------------------------------------------------------
# 3. Check / edit the data
# ---------------------------------------------------------------------------

if st.session_state.history is None:
    st.info("Load a history CSV or a sample to start.")
    st.stop()  # nothing more to show yet

st.header("3. Check the data")
st.caption("You can type in the table to correct a value. Leave a cell empty for a missing month. "
           "Use the + at the bottom of the table to add a month.")

# Show the table with "period" as a normal (editable) column.
table = st.session_state.history.reset_index()
edited = st.data_editor(
    table,
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    key=f"editor_{st.session_state.editor_version}",
    column_config={"period": st.column_config.TextColumn("period", help="e.g. 2026-09 or Sep 26")},
)

with st.expander("Add or rename a competitor"):
    c1, c2 = st.columns(2)
    new_name = c1.text_input("New competitor name")
    if c1.button("Add competitor", disabled=not new_name.strip()):
        base = st.session_state.get("edited_history", st.session_state.history)
        if new_name.strip() in base.columns:
            st.warning("That competitor already exists.")
        else:
            set_history(base.assign(**{new_name.strip(): float("nan")}))
            st.rerun()
    old = c2.selectbox("Rename", list(st.session_state.history.columns))
    renamed = c2.text_input("New name for it")
    if c2.button("Rename", disabled=not renamed.strip()):
        base = st.session_state.get("edited_history", st.session_state.history)
        if renamed.strip() in base.columns:
            st.warning("That name is already used. Rename can't merge two competitors.")
        else:
            set_history(base.rename(columns={old: renamed.strip()}))
            st.rerun()

# Check the edited table with the SAME rules as a CSV upload
# (turn it into CSV text and read it back).
try:
    csv_text = edited.to_csv(index=False)
    history = load_history(io.BytesIO(csv_text.encode("utf-8")), first_row=1)
    st.session_state.edited_history = history
except DataError as e:
    show_errors(e)
    st.stop()


# ---------------------------------------------------------------------------
# 4. Chart
# ---------------------------------------------------------------------------

st.header("4. Chart")

c1, c2, c3 = st.columns([3, 1, 1])
visible = c1.multiselect("Competitors to show", list(history.columns), default=list(history.columns),
                         help="Hiding a competitor keeps its data - it's just not drawn.")
show_values = c2.checkbox("Show values", value=True)
name_style = c3.radio("Names", ["box", "text"], horizontal=True,
                      format_func=lambda s: "Grey box" if s == "box" else "Plain text")

if not visible:
    st.warning("Select at least one competitor.")
    st.stop()

# --- Our site -----------------------------------------------------------------
options = ["(none)"] + visible
highlight = st.selectbox("Our site (thicker line, drawn on top)", options,
                         index=options.index("Fecon") if "Fecon" in options else 0)

# --- Y-axis -------------------------------------------------------------------
max_value = float(history[visible].max().max())
auto_top, auto_step = auto_axis(max_value)

with st.expander(f"Y-axis (automatic: 0 to {auto_top:,.0f} in steps of {auto_step:,.0f})"):
    manual = st.toggle("Set the axis myself")
    y_max = y_step = None
    if manual:
        # Start from the automatic values the first time the boxes appear.
        st.session_state.setdefault("y_max_input", float(auto_top))
        st.session_state.setdefault("y_step_input", float(auto_step))
        a1, a2 = st.columns(2)
        y_max = a1.number_input("Top of axis", min_value=1.0, step=float(auto_step),
                                format="%.0f", key="y_max_input")
        y_step = a2.number_input("Step (e.g. 2000 for 2K)", min_value=1.0,
                                 step=float(auto_step), format="%.0f", key="y_step_input")

        if max_value > y_max:
            def expand():
                # Round up to the next whole step above the highest value.
                st.session_state.y_max_input = float(-(-max_value // y_step) * y_step)

            st.warning(f"The highest value ({max_value:,.0f}) is above the top of the axis "
                       f"({y_max:,.0f}), so part of the chart will be cut off.")
            st.button("Expand axis to fit", on_click=expand)

# --- Colors -------------------------------------------------------------------
default_colors = pick_colors(list(history.columns))
with st.expander("Colors"):
    st.caption("Known competitors have fixed colors (Fecon is always red). Changes here last until "
               "you close the page - ask to add a color to DEFAULT_COLORS in chart.py to make it permanent.")
    picker_columns = st.columns(4)
    colors = {}
    for i, name in enumerate(visible):
        colors[name] = picker_columns[i % 4].color_picker(name, default_colors[name], key=f"color_{name}")

settings = ChartSettings(
    hidden=[n for n in history.columns if n not in visible],
    colors=colors,
    show_values=show_values,
    name_style=name_style,
    highlight=None if highlight == "(none)" else highlight,
    y_max=y_max,
    y_step=y_step,
)


@st.cache_data(show_spinner="Drawing chart...")
def make_chart(history, settings):
    """Remember finished charts so unchanged settings don't redraw."""
    return render_chart(history, settings)


try:
    png = make_chart(history, settings)
except ValueError as e:  # e.g. an axis step that is far too small
    st.error(str(e))
    st.stop()
st.image(png, width="stretch")

# --- Downloads -------------------------------------------------------------
default_name = f"chart_{history.index[0]}_to_{history.index[-1]}"
file_name = st.text_input("File name", default_name)

svg_settings = ChartSettings(**{**settings.__dict__, "file_format": "svg"})
d1, d2, d3 = st.columns(3)
d1.download_button("Download PNG (2727 x 1087)", png, f"{file_name}.png", "image/png", type="primary")
d2.download_button("Download SVG", make_chart(history, svg_settings), f"{file_name}.svg", "image/svg+xml")
d3.download_button("Download updated history CSV", history_to_csv(history),
                   f"{file_name}_history.csv", "text/csv",
                   help="Keep this file - upload it next month and add the new month to it.")

st.caption(f"{len(history)} months ({period_label(history.index[0])} - {period_label(history.index[-1])}), "
           f"{len(visible)} of {len(history.columns)} competitors shown.")
