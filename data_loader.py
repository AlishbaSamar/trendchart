"""
data_loader.py - reads CSV files and turns them into one clean table.

Every chart in this app is drawn from a "history" table that looks like this:

    period   | Fecon | Virnig | FAE Group | ...
    2026-01  | 3369  | 5710   | 3089      |
    2026-02  | 3534  | 5758   | 3234      |

  - one ROW per month
  - one COLUMN per competitor
  - an empty cell means "no data for that month" (the line will show a gap)

This file knows how to:
  1. load_history()        read a history CSV (wide or long format)
  2. load_semrush_month()  read one month's Semrush export and pick one metric
  3. add_month()           add that month to the history
  4. parse_number()        turn "20.4K", "173,120", "1.2M" into real numbers
"""

import csv
import io

import pandas as pd


class DataError(Exception):
    """Raised when a CSV has problems. Holds a list of readable messages."""

    def __init__(self, messages):
        self.messages = messages
        super().__init__("\n".join(messages))


# ---------------------------------------------------------------------------
# 1. Numbers
# ---------------------------------------------------------------------------

# Suffixes Semrush uses for rounded numbers.
MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

# Cell values that mean "no data".
EMPTY_VALUES = {"", "-", "n/a", "na", "none", "null"}


def parse_number(text):
    """
    Turn a cell from a CSV into a number.

        "173,120" -> 173120.0
        "20.4K"   -> 20400.0
        "1.2M"    -> 1200000.0
        "$1,500"  -> 1500.0
        ""        -> None   (missing value)
        "abc"     -> raises ValueError
    """
    if text is None:
        return None
    cleaned = str(text).strip()
    if cleaned.lower() in EMPTY_VALUES:
        return None

    # Remove things that are only there for display.
    cleaned = cleaned.replace(",", "").replace(" ", "").replace("$", "")

    multiplier = 1
    suffix = cleaned[-1:].upper()
    if suffix in MULTIPLIERS:
        multiplier = MULTIPLIERS[suffix]
        cleaned = cleaned[:-1]

    value = float(cleaned) * multiplier  # raises ValueError if not a number
    if value != value or value in (float("inf"), float("-inf")):  # NaN / infinity
        raise ValueError("not a finite number")
    return round(value, 6)


# ---------------------------------------------------------------------------
# 2. Months
# ---------------------------------------------------------------------------

# Month formats we accept in the "period" column. Tried in this order.
PERIOD_FORMATS = ["%Y-%m", "%Y-%m-%d", "%b %y", "%b %Y", "%B %Y", "%m/%Y"]


def parse_period(text):
    """
    Turn "2026-01", "Jan 26", "Jan 2026", "January 2026" or "01/2026"
    into a standard "2026-01". Raises ValueError if it can't.
    """
    cleaned = str(text).strip()
    for fmt in PERIOD_FORMATS:
        try:
            return pd.to_datetime(cleaned, format=fmt).strftime("%Y-%m")
        except (ValueError, TypeError):
            continue
    raise ValueError(f"'{text}' is not a month we understand (use e.g. 2026-01 or Jan 26)")


def period_label(period):
    """ "2026-01" -> "Jan 26"  (the text shown under the chart) """
    return pd.to_datetime(period, format="%Y-%m").strftime("%b %y")


# ---------------------------------------------------------------------------
# 3. Reading files
# ---------------------------------------------------------------------------

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB


def _read_text(source):
    """
    Accept a file path OR an uploaded file (Streamlit gives us bytes)
    and return the file's text.
    """
    if hasattr(source, "read"):  # uploaded file / open file object
        raw = source.read()
    else:  # a path on disk
        with open(source, "rb") as f:
            raw = f.read()

    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) > MAX_FILE_BYTES:
        raise DataError(["File is larger than 5 MB."])
    try:
        # "utf-8-sig" also removes the invisible marker Excel adds at the start.
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise DataError(["File is not UTF-8 text. In Excel use 'Save As > CSV UTF-8'."])


def _read_table(text):
    """Read CSV text into a DataFrame where every cell is still text."""
    header = next(csv.reader(io.StringIO(text)), [])
    header = [h.strip() for h in header]
    if not header or all(h == "" for h in header):
        raise DataError(["The file is empty."])

    duplicates = sorted({h for h in header if h and header.count(h) > 1})
    if duplicates:
        raise DataError([f"Column '{d}' appears more than once in the header." for d in duplicates])

    try:
        table = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, skipinitialspace=True)
    except pd.errors.ParserError as e:
        raise DataError([f"The CSV is malformed: {e}"])
    table.columns = [c.strip() for c in table.columns]
    return table


# ---------------------------------------------------------------------------
# 4. History files (the main input)
# ---------------------------------------------------------------------------

def load_history(source, first_row=2):
    """
    Read a history CSV and return a clean DataFrame:
      - index   = period ("2026-01", ...), sorted oldest first
      - columns = competitor names
      - values  = numbers (NaN where missing)

    Accepts two layouts:
      WIDE:  period,Fecon,Virnig,...      (one column per competitor)
      LONG:  period,series,value          (one row per month+competitor)

    first_row : the number shown in error messages for the first data row.
                2 for a CSV file (row 1 is the header), 1 for the app's table.
    """
    table = _read_table(_read_text(source))
    lower_cols = [c.lower() for c in table.columns]

    if "period" not in lower_cols:
        raise DataError(["The first column must be called 'period' (the month)."])

    # Rename "Period"/"PERIOD" etc. to exactly "period".
    table = table.rename(columns={c: c.lower() for c in table.columns if c.lower() in ("period", "series", "value")})

    if set(lower_cols) == {"period", "series", "value"}:
        return _load_long(table, first_row)
    return _load_wide(table, first_row)


def _load_wide(table, first_row):
    errors = []
    competitors = [c for c in table.columns if c != "period"]
    if not competitors:
        errors.append("No competitor columns found. Add at least one column after 'period'.")
    if any(c == "" or c.startswith("Unnamed") for c in competitors):
        errors.append("One of the competitor columns has no name in the header.")

    rows = {}
    for i, row in table.iterrows():
        line = i + first_row
        if all(str(cell).strip() == "" for cell in row):
            continue  # skip completely empty rows

        try:
            period = parse_period(row["period"])
        except ValueError as e:
            errors.append(f"Row {line}, column 'period': {e}")
            continue
        if period in rows:
            errors.append(f"Row {line}: month {period} appears twice (see earlier row).")
            continue

        values = {}
        for name in competitors:
            try:
                values[name] = parse_number(row[name])
            except ValueError:
                errors.append(f"Row {line}, column '{name}': '{row[name]}' is not a number.")
        rows[period] = values

    if errors:
        raise DataError(errors)
    return _finish(pd.DataFrame.from_dict(rows, orient="index", columns=competitors))


def _load_long(table, first_row):
    errors = []
    cells = {}  # (period, competitor) -> value
    first_seen = {}  # remembers which row each (period, competitor) came from
    order = []  # keep competitors in the order they first appear

    for i, row in table.iterrows():
        line = i + first_row
        if all(str(cell).strip() == "" for cell in row):
            continue
        name = row["series"].strip()
        if not name:
            errors.append(f"Row {line}, column 'series': competitor name is empty.")
            continue
        try:
            period = parse_period(row["period"])
            value = parse_number(row["value"])
        except ValueError as e:
            errors.append(f"Row {line}: {e}")
            continue

        key = (period, name)
        if key in cells:
            errors.append(f"Row {line}: {name} / {period} already given in row {first_seen[key]}.")
            continue
        cells[key] = value
        first_seen[key] = line
        if name not in order:
            order.append(name)

    if errors:
        raise DataError(errors)

    wide = pd.Series(cells).unstack()  # periods become rows, names become columns
    return _finish(wide[order])


def _finish(history):
    """Final clean-up shared by both layouts."""
    history = history.sort_index().astype(float)
    history.index.name = "period"
    if len(history) < 2:
        raise DataError(["At least 2 months are needed to draw a line."])
    return history


# ---------------------------------------------------------------------------
# 5. Semrush monthly exports
# ---------------------------------------------------------------------------

def load_semrush_month(source):
    """
    Read a Semrush competitor export like fecon_red_line_aug_2026.csv:

        Website,Domain Overview,Worldwide Traffic,US Traffic,Top 3,...
        Virnig,31,9.6K,8.9K,235,...

    Returns a DataFrame: index = competitor name, columns = metrics (numbers).
    """
    table = _read_table(_read_text(source))
    name_col = table.columns[0]  # first column holds the website names ("Website")
    metrics = list(table.columns[1:])

    errors = []
    data = {}
    for i, row in table.iterrows():
        line = i + 2
        name = row[name_col].strip()
        if not name:
            errors.append(f"Row {line}: website name is empty.")
            continue
        if name in data:
            errors.append(f"Row {line}: '{name}' appears twice.")
            continue
        values = {}
        for metric in metrics:
            try:
                values[metric] = parse_number(row[metric])
            except ValueError:
                errors.append(f"Row {line}, column '{metric}': '{row[metric]}' is not a number.")
        data[name] = values

    if errors:
        raise DataError(errors)
    result = pd.DataFrame.from_dict(data, orient="index", columns=metrics).astype(float)
    result.index.name = "competitor"
    return result


def add_month(history, period, values, replace=False):
    """
    Add one month to a history table and return the NEW table
    (the original is not changed).

    history : DataFrame from load_history() (or None to start fresh)
    period  : "2026-09", "Sep 26", ...
    values  : {"Fecon": 2546, "Virnig": 3642, ...}  or a pandas Series
    replace : if the month already exists, overwrite it (otherwise error)

    A competitor that's new this month gets a new column (empty for older months).
    A competitor missing this month gets an empty cell (a gap in its line).
    """
    period = parse_period(period)
    values = pd.Series(values, dtype=float)

    if history is None:
        history = pd.DataFrame(dtype=float)
    if period in history.index and not replace:
        raise DataError([f"Month {period} is already in the history. Tick 'replace' to overwrite it."])

    updated = history.copy()
    for name in values.index:
        if name not in updated.columns:
            updated[name] = float("nan")
    updated.loc[period] = values.reindex(updated.columns)
    updated = updated.sort_index()
    updated.index.name = "period"
    return updated


def history_to_csv(history):
    """Turn a history table back into CSV text (for the 'download updated history' button)."""
    out = history.copy()
    # Whole numbers are written without ".0" so the file stays readable.
    out = out.map(lambda v: "" if pd.isna(v) else (int(v) if float(v).is_integer() else v))
    return out.to_csv()


# ---------------------------------------------------------------------------
# Try it:   python data_loader.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", None)

    print("=== Top 100 history (wide format) ===")
    top100 = load_history("sample_data/fecon_top100_history.csv")
    print(top100, "\n")

    print("=== Traffic history (has some empty cells) ===")
    print(load_history("sample_data/fecon_traffic_history.csv"), "\n")

    print("=== Semrush monthly export ===")
    semrush = load_semrush_month("sample_data/fecon_red_line_aug_2026.csv")
    print(semrush, "\n")

    print("=== Adding 'Top 100' from the Semrush file as Sep 2026 ===")
    print(add_month(top100, "Sep 26", semrush["Top 100"]), "\n")

    print("=== Error example ===")
    bad = io.BytesIO(b"period,Fecon,Virnig\n2026-01,100,200\n2026-02,abc,300\n2026-02,1,2\n")
    try:
        load_history(bad)
    except DataError as e:
        for message in e.messages:
            print("  -", message)
