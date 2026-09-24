"""
insights.py - the numbers behind the dashboard tiles and tables.

All functions take one chart's history table (rows = months, columns =
competitors) plus the list of competitors that are shown, and compare the
latest month with the month before it.
"""

import math

import pandas as pd


def trend(series):
    """The months that have a value, for the small trend lines (empty months are skipped)."""
    return [float(v) for v in series if not pd.isna(v)]


def latest_months(history):
    """(latest month, month before it or None)"""
    periods = list(history.index)
    return periods[-1], (periods[-2] if len(periods) > 1 else None)


def _value(history, period, name):
    if period is None or name not in history.columns:
        return None
    value = history.at[period, name]
    return None if pd.isna(value) else float(value)


def leaderboard(history, names):
    """
    One row per competitor for the latest month, best first:
    rank, value, change vs the month before (number and %), share of the
    total, and all monthly values (for a small trend line).
    """
    last, previous = latest_months(history)
    rows = []
    for name in names:
        value = _value(history, last, name)
        if value is None:
            continue
        before = _value(history, previous, name)
        change = None if before is None else value - before
        rows.append({
            "Competitor": name,
            "Value": value,
            "Change": change,
            "Change %": (change / before) if change is not None and before else None,
            "Trend": trend(history[name]),
        })

    table = pd.DataFrame(rows, columns=["Competitor", "Value", "Change", "Change %", "Trend"])
    table = table.sort_values("Value", ascending=False, kind="stable").reset_index(drop=True)
    total = table["Value"].sum()
    table.insert(0, "Rank", range(1, len(table) + 1))
    table.insert(4, "Share", table["Value"] / total if total else 0.0)
    return table


def rank_of(history, names, name, period):
    """Place of `name` among `names` in that month (1 = highest), or None."""
    values = {n: _value(history, period, n) for n in names}
    if values.get(name) is None:
        return None
    return 1 + sum(1 for n, v in values.items() if v is not None and v > values[name])


def site_summary(history, names, site):
    """Everything the tiles need about one site in this chart (or None if it has no data)."""
    last, previous = latest_months(history)
    value = _value(history, last, site)
    if value is None:
        return None
    before = _value(history, previous, site)
    rank = rank_of(history, names, site, last)
    rank_before = rank_of(history, names, site, previous)
    return {
        "value": value,
        "change": None if before is None else value - before,
        "change_pct": None if before in (None, 0) else (value - before) / before,
        "rank": rank,
        "rank_move": None if rank_before is None else rank_before - rank,  # + = climbed
        "of": sum(1 for n in names if _value(history, last, n) is not None),
        "trend": trend(history[site]),
    }


def biggest_mover(board):
    """The competitor whose value changed the most since last month (row of the leaderboard)."""
    moved = board.dropna(subset=["Change"])
    if moved.empty:
        return None
    return moved.loc[moved["Change"].abs().idxmax()]


def fmt(value):
    """12345.0 -> '12,345'"""
    return "–" if _missing(value) else f"{value:,.0f}"


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def fmt_change(change, pct=None):
    """(+1234, 0.056) -> '+1,234 (+5.6%)'   (None when there is nothing to compare with)"""
    if _missing(change):
        return None
    text = f"{change:+,.0f}"
    if not _missing(pct):
        text += f" ({pct:+.1%})"
    return text


if __name__ == "__main__":
    from data_loader import load_histories

    h = load_histories("sample_data/fecon_all_charts_history.csv")["US Traffic"]
    names = list(h.columns)
    pd.set_option("display.width", 200)
    print(leaderboard(h, names).drop(columns="Trend"))
    print(site_summary(h, names, "Fecon"))
    print("mover:", dict(biggest_mover(leaderboard(h, names))))
