"""
chart.py - draws the competitor trend chart.

The one function the rest of the app needs:

    image_bytes = render_chart(history, ChartSettings(...))

  history  = the table from data_loader.load_history()
             (rows = months, columns = competitors)
  settings = what to show and how (all optional)

It returns the finished PNG or SVG as bytes, so the web page can show it
or offer it as a download. Nothing is random: the same data + settings
always gives exactly the same image.

Style values come from Manus's script 04 and the PRD (section 10.1).
"""

import io
import math
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to memory, no window (must come before pyplot)

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

from data_loader import period_label

# ---------------------------------------------------------------------------
# Font: use the bundled Liberation Sans so the chart looks the same on every PC
# ---------------------------------------------------------------------------

FONT_PATH = Path(__file__).parent / "fonts" / "LiberationSans-Regular.ttf"
font_manager.fontManager.addfont(str(FONT_PATH))
FONT_NAME = FontProperties(fname=str(FONT_PATH)).get_name()

plt.rcParams.update({
    "font.family": FONT_NAME,
    "svg.hashsalt": "chartmaker",  # stable ids inside SVG files
})

# ---------------------------------------------------------------------------
# Style (TrueGrit template)
# ---------------------------------------------------------------------------

AXIS_TEXT_COLOR = "#737373"
AXIS_FONT_SIZE = 18
VALUE_COLOR = "#343434"
VALUE_FONT_SIZE = 17
NAME_FONT_SIZE = 18
GRID_COLOR = "#F3F3F3"
BOX_COLOR = "#FAFAFA"
LEADER_COLOR = "#D7D7D7"
LINE_WIDTH = 3.2
HIGHLIGHT_LINE_WIDTH = 5.0
MARKER_SIZE = 5.5

# Fixed colors so a competitor keeps its color every month (from Manus's charts).
DEFAULT_COLORS = {
    "Fecon": "#DE061D",
    "Virnig": "#EF6CC1",
    "Diamond Mower": "#FD7804",
    "FAE Group": "#0A9C08",
    "Loftness": "#C4C4C4",
    "Prinoth": "#12BECA",
    "Denis Cimaf": "#F9B570",
    "Shearex": "#915348",
    "Mastodon": "#FCB4D0",
    "New Holland": "#9665BE",
    "Vermeer": "#84DF80",
}

# Colors for competitors not listed above, used in this order.
# (No red here: red is kept for our own site, Fecon.)
EXTRA_COLORS = [
    "#1F77B4", "#2CA02C", "#9467BD", "#8C564B", "#6B6ECF",
    "#17BECF", "#BCBD22", "#FF7F0E", "#7F7F7F", "#393B79",
    "#637939", "#8C6D31", "#843C39", "#7B4173", "#3182BD",
]


@dataclass
class ChartSettings:
    """Everything the user can change. Every field has a sensible default."""

    hidden: list = field(default_factory=list)  # competitor names NOT to draw
    colors: dict = field(default_factory=dict)  # {"Virnig": "#EF6CC1"} overrides
    show_values: bool = True  # print the number at every point
    # How competitor names are shown:
    #   "callout" = grey box inside the chart with a straight line to its line (Manus style)
    #   "box"     = grey box at the right end of each line
    #   "text"    = plain colored text at the right end of each line
    name_style: str = "callout"
    highlight: str | None = None  # our own site, e.g. "Fecon": thicker line, drawn on top

    # y-axis: leave both as None for automatic.
    # Manual values are used exactly - points above y_max are cut off (the app warns first).
    y_max: float | None = None
    y_step: float | None = None

    # image size (PRD default: 2727 x 1087 pixels)
    width_px: int = 2727
    height_px: int = 1087
    dpi: int = 100
    file_format: str = "png"  # "png" or "svg"


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

def pick_colors(names, overrides=None):
    """Give every competitor a color: user choice > fixed default > next spare color."""
    overrides = overrides or {}
    result = {}
    for name in names:
        if name in overrides:
            result[name] = overrides[name]
        elif name in DEFAULT_COLORS:
            result[name] = DEFAULT_COLORS[name]

    spare = [c for c in EXTRA_COLORS if c not in result.values()]
    for name in names:
        if name not in result:
            result[name] = spare.pop(0) if spare else "#555555"
    return result


def readable_text_color(color):
    """
    Pale colors (light grey, light pink) are hard to read as text on white.
    Lines keep their exact color; only text gets darkened a bit.
    """
    r, g, b = mcolors.to_rgb(color)
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    if brightness < 0.55:
        return color
    darker = 0.55 / brightness
    return mcolors.to_hex((r * darker, g * darker, b * darker))


# ---------------------------------------------------------------------------
# Y-axis
# ---------------------------------------------------------------------------

def nice_step(max_value, max_ticks=11):
    """
    Choose a readable step (1, 2, 5, 10, 20, 50, ...) so the axis has
    at most `max_ticks` steps.   21,739 -> 2,000    5,758 -> 1,000
    """
    if max_value <= 0:
        return 1
    rough = max_value / max_ticks
    power = 10 ** math.floor(math.log10(rough))
    for multiple in (1, 2, 5, 10):
        if multiple * power >= rough:
            return multiple * power
    return 10 * power


def format_tick(value, top):
    """
    Axis label. The unit depends on how high the whole axis goes (`top`):
      axis up to 22,000    : 0 -> "0K", 2000 -> "2K", 2500 -> "2.5K"
      axis up to 2,000,000 : "0M", "0.5M", "1M"
      axis up to 40 (DA)   : "0", "10", "20"
    """
    if top >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    if top >= 1_000:
        return f"{value / 1_000:g}K"
    return f"{value:g}"


def auto_axis(max_value):
    """Automatic (top tick, step). 21,739 -> (22,000, 2,000)"""
    step = nice_step(max_value)
    return math.ceil(max_value / step) * step, step


def y_axis(max_value, settings):
    """Return (ticks, top of the axis). Manual settings win over automatic."""
    auto_top, auto_step = auto_axis(max_value)
    step = settings.y_step or auto_step
    top_tick = settings.y_max or (math.ceil(max_value / step) * step if settings.y_step else auto_top)
    if top_tick / step > 60:
        raise ValueError(f"A step of {step:,.0f} would draw more than 60 grid lines. Use a bigger step.")
    ticks = np.arange(0, top_tick + step / 2, step)
    return ticks, top_tick


# ---------------------------------------------------------------------------
# Label placement - the part that stops labels from overlapping
# ---------------------------------------------------------------------------

def spread_labels(wanted, height, low, high, order=None):
    """
    Move labels up/down so none overlap, keeping each as close as
    possible to where it wants to be.

    wanted : list of y-positions (pixels) where each label would like to sit
    height : how tall one label is (pixels) - the minimum gap between centers
    low/high : labels must stay between these y-positions
    order  : bottom-to-top order the labels must keep (default: by wanted position).
             We pass the order of the POINTS, so a higher point always gets a higher label.

    Returns the final y-position of every label (same order as `wanted`).

    How: go through labels from bottom to top. Labels that would overlap
    are glued into a "group". A group sits centred on the average of what
    its members wanted, then gets pushed inside the low/high limits.
    Because we only sort and average, the result is always the same.
    """
    if order is None:
        order = sorted(range(len(wanted)), key=lambda i: wanted[i])
    groups = []  # each group: {"members": [...], "bottom": y of the lowest label}

    def place(group):
        members = group["members"]
        # Centre the stack on the average wanted position...
        group["bottom"] = sum(wanted[m] - k * height for k, m in enumerate(members)) / len(members)
        # ...but keep it inside the allowed area.
        top_limit = high - (len(members) - 1) * height
        group["bottom"] = max(low, min(group["bottom"], top_limit))

    for i in order:
        group = {"members": [i]}
        place(group)
        groups.append(group)
        # Merge with the group below while they overlap.
        while len(groups) > 1:
            below, current = groups[-2], groups[-1]
            below_top = below["bottom"] + (len(below["members"]) - 1) * height
            if current["bottom"] - below_top >= height:
                break
            merged = {"members": below["members"] + current["members"]}
            place(merged)
            groups[-2:] = [merged]

    final = [0.0] * len(wanted)
    for group in groups:
        for k, m in enumerate(group["members"]):
            final[m] = group["bottom"] + k * height
    return final


def text_width_pt(text, size):
    """Width of a piece of text in points (1 pt = 1/72 inch)."""
    return TextPath((0, 0), text, size=size, prop=FontProperties(fname=str(FONT_PATH))).get_extents().width


# ---------------------------------------------------------------------------
# The main function
# ---------------------------------------------------------------------------

def render_chart(history, settings=None):
    """Draw the chart and return it as PNG or SVG bytes."""
    settings = settings or ChartSettings()

    names = [n for n in history.columns if n not in settings.hidden and history[n].notna().any()]
    if not names:
        raise ValueError("Nothing to draw: every competitor is hidden or empty.")
    colors = pick_colors(list(history.columns), settings.colors)

    periods = list(history.index)
    x = np.arange(len(periods))
    max_value = float(history[names].max().max())
    ticks, top_tick = y_axis(max_value, settings)

    dpi = settings.dpi
    px_per_pt = dpi / 72  # converts font sizes (points) to pixels

    fig, ax = plt.subplots(figsize=(settings.width_px / dpi, settings.height_px / dpi),
                           dpi=dpi, facecolor="white")
    try:
        fig.subplots_adjust(left=0.035, right=0.985, top=0.975, bottom=0.105)

        names_at_end = settings.name_style in ("box", "text")
        if names_at_end:
            # --- Make room on the right for the competitor names ------------
            # Space between the last point and its name: wide enough that the
            # last month's numbers (centred on the point) never touch the names.
            last_values = [history[n].dropna().iloc[-1] for n in names]
            widest_value = max(text_width_pt(f"{v:,.0f}", VALUE_FONT_SIZE) for v in last_values)
            name_gap_pt = max(34, widest_value / 2 + 14) if settings.show_values else 16
            box_pad = 0.35 if settings.name_style == "box" else 0.1
            longest = max(text_width_pt(n, NAME_FONT_SIZE) for n in names)
            names_space_px = (name_gap_pt + longest + 2 * box_pad * NAME_FONT_SIZE + 8) * px_per_pt
            axes_width_px = settings.width_px * (0.985 - 0.035)
            span = len(periods) - 0.52
            right_extra = names_space_px * span / (axes_width_px - names_space_px)
            ax.set_xlim(-0.48, len(periods) - 1 + max(0.52, right_extra))
        else:
            ax.set_xlim(-0.48, len(periods) - 0.52)  # same as Manus's chart

        # --- Y axis: leave a little headroom above the highest value --------
        headroom = top_tick * 0.06  # room above the highest point for its label
        top = top_tick if settings.y_max else max(top_tick, max_value)
        ax.set_ylim(0, top + headroom)
        ax.set_yticks(ticks)
        ax.set_yticklabels([format_tick(t, top_tick) for t in ticks], color=AXIS_TEXT_COLOR, fontsize=AXIS_FONT_SIZE)
        ax.set_xticks(x)
        ax.set_xticklabels([period_label(p) for p in periods], color=AXIS_TEXT_COLOR, fontsize=AXIS_FONT_SIZE)

        # --- Clean look: only light horizontal grid lines -------------------
        ax.tick_params(axis="both", length=0, pad=14)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=1.2)
        ax.grid(axis="x", visible=False)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # --- Lines -----------------------------------------------------------
        # Our own site is drawn last (on top of the others) with a thicker line.
        draw_order = [n for n in names if n != settings.highlight] + [n for n in names if n == settings.highlight]
        for name in draw_order:
            is_ours = name == settings.highlight
            ax.plot(x, history[name].to_numpy(), color=colors[name],
                    linewidth=HIGHLIGHT_LINE_WIDTH if is_ours else LINE_WIDTH,
                    marker="o", markersize=MARKER_SIZE * 1.4 if is_ours else MARKER_SIZE,
                    markeredgewidth=0, solid_capstyle="round", zorder=4 if is_ours else 3)
            # Missing months are NaN -> matplotlib leaves a gap in the line.

        # From here on we work in pixels, so we can measure distances exactly.
        def to_px(xv, yv):
            return ax.transData.transform((xv, yv))

        y_floor = to_px(0, 0)[1]
        y_ceiling = to_px(0, ax.get_ylim()[1])[1]

        value_boxes = []  # where the numbers ended up, so name boxes can avoid them
        if settings.show_values:
            value_boxes = _add_value_labels(ax, history, names, colors, x, to_px, y_floor, y_ceiling, px_per_pt)
        if names_at_end:
            _add_name_labels(ax, history, names, colors, to_px, y_floor, y_ceiling,
                             px_per_pt, name_gap_pt, settings.name_style, box_pad)
        else:
            _add_callouts(ax, history, names, colors, to_px, value_boxes, px_per_pt)

        buffer = io.BytesIO()
        fig.savefig(buffer, format=settings.file_format, dpi=dpi, facecolor="white",
                    metadata={"Date": None} if settings.file_format == "svg" else None)
        return buffer.getvalue()
    finally:
        plt.close(fig)  # always free memory, even if something failed


def _add_value_labels(ax, history, names, colors, x, to_px, y_floor, y_ceiling, px_per_pt):
    """
    Print the number at every point, month by month, without overlaps.
    Returns the pixel rectangle (left, bottom, right, top) of every number.
    """
    label_h = VALUE_FONT_SIZE * 1.3 * px_per_pt  # label height incl. a little air
    gap = 5 * px_per_pt  # distance between a point and its label
    boxes = []

    for i in range(len(x)):
        points = []  # (name, value, pixel y of the point, wanted pixel y of label)
        for name in names:
            values = history[name].to_numpy()
            value = values[i]
            if np.isnan(value):
                continue
            point_y = to_px(i, value)[1]

            # Put the label BELOW if this point is a dip (lower than its
            # neighbours), otherwise ABOVE - so it doesn't sit on its own line.
            neighbours = [values[j] for j in (i - 1, i + 1) if 0 <= j < len(values) and not np.isnan(values[j])]
            is_dip = bool(neighbours) and all(n > value for n in neighbours)
            offset = label_h / 2 + gap
            wanted = point_y - offset if is_dip else point_y + offset
            points.append((name, value, point_y, wanted))

        # Keep labels in the same up/down order as their points.
        point_order = sorted(range(len(points)), key=lambda k: (points[k][2], points[k][3]))
        final = spread_labels([p[3] for p in points], label_h,
                              low=y_floor + label_h / 2, high=y_ceiling - label_h / 2,
                              order=point_order)

        point_x = to_px(i, 0)[0]
        for (name, value, point_y, wanted), label_y in zip(points, final):
            # A label squeezed into a stack with other labels is written in its
            # line's color, so you can still tell which line it belongs to.
            crowded = sum(abs(label_y - other) < label_h * 1.05 for other in final) > 1
            text_color = readable_text_color(colors[name]) if crowded else VALUE_COLOR
            text = f"{value:,.0f}"
            half_w = text_width_pt(text, VALUE_FONT_SIZE) * px_per_pt / 2 + 4
            boxes.append((point_x - half_w, label_y - label_h / 2, point_x + half_w, label_y + label_h / 2))
            ax.annotate(
                text,
                xy=(i, value),
                xytext=(0, (label_y - point_y) / px_per_pt),  # offset in points
                textcoords="offset points",
                ha="center", va="center",
                fontsize=VALUE_FONT_SIZE, color=text_color, zorder=6,
                # White background so a line passing behind never hides the number.
                bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.85),
            )
    return boxes


# ---------------------------------------------------------------------------
# Callouts: a grey name box inside the chart with a straight line to its line
# ---------------------------------------------------------------------------

CALLOUT_PAD = 0.55  # space around the name inside its box (x font size)

# How "bad" each problem is when choosing a spot for a name box.
# The lowest total wins. 1 point = 1 pixel of leader-line length.
COST_CROSSES_LINE = 260  # a line runs through the box
COST_COVERS_DOT = 400  # a data point is hidden under the box
COST_LEADER_CROSSES = 120  # the leader line crosses another line
COST_COVERS_LEADER = 260  # the box covers another box's leader line


def _boxes_overlap(a, b, margin=0.0):
    return a[0] < b[2] + margin and b[0] < a[2] + margin and a[1] < b[3] + margin and b[1] < a[3] + margin


def _clip(x0, y0, x1, y1, box):
    """Does the straight line (x0,y0)-(x1,y1) pass through the rectangle? (Liang-Barsky clipping)"""
    dx, dy = x1 - x0, y1 - y0
    t_in, t_out = 0.0, 1.0
    for p, q in ((-dx, x0 - box[0]), (dx, box[2] - x0), (-dy, y0 - box[1]), (dy, box[3] - y0)):
        if p == 0:
            if q < 0:
                return False  # parallel to this edge and outside it
            continue
        t = q / p
        if p < 0:
            t_in = max(t_in, t)  # entering
        else:
            t_out = min(t_out, t)  # leaving
        if t_in > t_out:
            return False
    return True


def _vertical_crosses(x, y_low, y_high, p, q):
    """Does the vertical line at x (from y_low to y_high) cross the segment p-q?"""
    (x0, y0), (x1, y1) = p, q
    if x0 == x1 or not (min(x0, x1) <= x <= max(x0, x1)):
        return False
    y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return y_low < y < y_high


def _add_callouts(ax, history, names, colors, to_px, value_boxes, px_per_pt):
    """
    Put each competitor's name in a grey box near its line, with a straight
    vertical leader line to the line - like the Manus chart, but the spots
    are chosen automatically:

      1. Try many spots: several places along the line, above and below it,
         at different distances.
      2. Score each spot (see the COST_ values): covering a number or another
         name box is never allowed; covering lines, dots or leaders costs
         points; every pixel of leader line costs 1 point.
      3. Take the cheapest spot. Same data -> same spots, every time.
    """
    plot = ax.bbox.extents  # (left, bottom, right, top) of the drawing area, in pixels
    pad_px = CALLOUT_PAD * NAME_FONT_SIZE * px_per_pt
    box_h = NAME_FONT_SIZE * 1.15 * px_per_pt + 2 * pad_px
    months = list(history.index)

    # Every line piece and every dot, in pixels.
    segments = {}  # name -> list of ((x0, y0), (x1, y1))
    dots = []
    for name in names:
        values = history[name].to_numpy()
        pts = [None if np.isnan(v) else tuple(to_px(i, v)) for i, v in enumerate(values)]
        dots += [p for p in pts if p is not None]
        segments[name] = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1) if pts[i] and pts[i + 1]]
    all_segments = [seg for segs in segments.values() for seg in segs]

    placed_boxes = []
    placed_leaders = []  # (x, y_bottom, y_top)

    # Lines lowest down have the least free space (nothing below 0), so they choose first.
    order = sorted(names, key=lambda n: (history[n].mean(), n))
    for name in order:
        values = history[name].to_numpy()
        box_w = text_width_pt(name, NAME_FONT_SIZE) * px_per_pt + 2 * pad_px

        # Candidate spots: (leader length, anchor point on the line, box, above/below)
        candidates = []
        for i in range(len(months) - 1):
            if np.isnan(values[i]) or np.isnan(values[i + 1]):
                continue
            for t in (0.5, 0.35, 0.65, 0.2, 0.8):
                anchor_x, anchor_y = to_px(i + t, values[i] + (values[i + 1] - values[i]) * t)
                for side in (1, -1):  # 1 = box above the line, -1 = below
                    for dist in range(int(12 * px_per_pt), int(plot[3] - plot[1]), 14):
                        centre_y = anchor_y + side * (dist + box_h / 2)
                        box = (anchor_x - box_w / 2, centre_y - box_h / 2,
                               anchor_x + box_w / 2, centre_y + box_h / 2)
                        if box[0] < plot[0] or box[2] > plot[2] or box[1] < plot[1] or box[3] > plot[3]:
                            continue  # would stick out of the chart
                        candidates.append((dist, anchor_x, anchor_y, box, side))
        candidates.sort(key=lambda c: c[0])  # shortest leader first

        best = None
        for dist, anchor_x, anchor_y, box, side in candidates:
            if best and dist >= best[0]:
                break  # every remaining spot has a longer leader, so none can win
            # Never allowed: covering a number or another name box.
            if any(_boxes_overlap(box, other, 3) for other in value_boxes + placed_boxes):
                continue
            leader = (anchor_x, anchor_y, box[1]) if side == 1 else (anchor_x, box[3], anchor_y)
            cost = dist
            cost += COST_CROSSES_LINE * sum(_clip(*p, *q, box) for p, q in all_segments)
            cost += COST_COVERS_DOT * sum(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in dots)
            cost += COST_LEADER_CROSSES * sum(
                _vertical_crosses(*leader, p, q)
                for other, segs in segments.items() if other != name for p, q in segs)
            cost += COST_COVERS_LEADER * sum(_clip(x, y0, x, y1, box) for x, y0, y1 in placed_leaders)
            # A leader running through a number would hide it.
            cost += COST_CROSSES_LINE * sum(_clip(leader[0], leader[1], leader[0], leader[2], other)
                                            for other in value_boxes)
            if best is None or cost < best[0]:
                best = (cost, anchor_x, anchor_y, box, leader)

        if best is None:
            continue  # no free space at all (extremely crowded) - skip rather than overlap
        _, anchor_x, anchor_y, box, leader = best
        placed_boxes.append(box)
        placed_leaders.append(leader)

        to_data = ax.transData.inverted()
        anchor = to_data.transform((anchor_x, anchor_y))
        centre = to_data.transform(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))
        ax.annotate(
            name, xy=anchor, xytext=centre, textcoords="data",
            ha="center", va="center", fontsize=NAME_FONT_SIZE,
            color=readable_text_color(colors[name]), zorder=8,
            bbox=dict(boxstyle=f"square,pad={CALLOUT_PAD}", facecolor=BOX_COLOR, edgecolor="none", alpha=0.96),
            arrowprops=dict(arrowstyle="-", color=LEADER_COLOR, linewidth=2.0, shrinkA=0, shrinkB=0),
        )


def _add_name_labels(ax, history, names, colors, to_px, y_floor, y_ceiling,
                     px_per_pt, name_gap_pt, style, box_pad):
    """Write each competitor's name just right of the last point of its line."""
    if style == "box":
        label_h = NAME_FONT_SIZE * (1.2 + 2 * box_pad) * px_per_pt + 4
    else:
        label_h = NAME_FONT_SIZE * 1.3 * px_per_pt

    ends = []  # (name, x of last point, value, pixel y)
    for name in names:
        series = history[name]
        last_period = series.last_valid_index()
        last_x = list(history.index).index(last_period)
        value = series[last_period]
        ends.append((name, last_x, value, to_px(last_x, value)[1]))

    point_order = sorted(range(len(ends)), key=lambda k: ends[k][3])
    final = spread_labels([e[3] for e in ends], label_h,
                          low=y_floor + label_h / 2, high=y_ceiling - label_h / 2,
                          order=point_order)

    for (name, last_x, value, point_y), label_y in zip(ends, final):
        moved = abs(label_y - point_y) > label_h * 0.3
        box = None
        if style == "box":
            box = dict(boxstyle=f"square,pad={box_pad}", facecolor=BOX_COLOR, edgecolor="none", alpha=0.96)
        ax.annotate(
            name,
            xy=(last_x, value),
            xytext=(name_gap_pt, (label_y - point_y) / px_per_pt),
            textcoords="offset points",
            ha="left", va="center",
            fontsize=NAME_FONT_SIZE, color=readable_text_color(colors[name]), zorder=8,
            bbox=box,
            arrowprops=dict(arrowstyle="-", color=LEADER_COLOR, linewidth=2.0,
                            shrinkA=0, shrinkB=6) if moved else None,
        )


# ---------------------------------------------------------------------------
# Try it:   python chart.py      -> writes test charts into output/
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from data_loader import load_history

    out = Path("output")
    out.mkdir(exist_ok=True)

    tests = {
        "test_top100.png": ("sample_data/fecon_top100_history.csv", ChartSettings()),
        "test_traffic.png": ("sample_data/fecon_traffic_history.csv", ChartSettings()),
        "test_traffic_plain_names.png": ("sample_data/fecon_traffic_history.csv", ChartSettings(name_style="text")),
        "test_traffic_names_at_end.png": ("sample_data/fecon_traffic_history.csv", ChartSettings(name_style="box")),
        "test_top100_big_only.png": ("sample_data/fecon_top100_history.csv",
                                     ChartSettings(hidden=["Prinoth", "Denis Cimaf", "Shearex", "Mastodon"])),
        "test_traffic.svg": ("sample_data/fecon_traffic_history.csv", ChartSettings(file_format="svg")),
        "test_top100_2k_highlight.png": ("sample_data/fecon_top100_history.csv",
                                         ChartSettings(highlight="Fecon", y_max=6000, y_step=2000,
                                                       colors={"Loftness": "#7F7F7F"})),
    }
    for filename, (csv_path, settings) in tests.items():
        data = render_chart(load_history(csv_path), settings)
        (out / filename).write_bytes(data)
        print(f"wrote output/{filename}  ({len(data) // 1024} KB)")
