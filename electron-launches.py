import marimo

__generated_with = "0.19.6"
app = marimo.App(width="full")

with app.setup(hide_code=True):
    import marimo as mo
    import pandas as pd
    import warnings

    # Suppress expected pandas warnings about timezone info being dropped when converting to Period
    # This is expected behavior - Period objects don't support timezones
    warnings.filterwarnings("ignore", ".*will drop timezone information.*", UserWarning)


@app.cell
def _():
    df_electron = load_electron_data()
    df_electron["Launch_Date_ET"] = parse_vague_dates_to_eastern(
        df_electron["Launch_Date"], tz="America/New_York", output_type="datetime"
    )
    return (df_electron,)


@app.cell
def _(df_electron):
    # Interactive controls for filtering
    period_control = mo.ui.dropdown(
        options=["month", "quarter", "year"],
        value="quarter",
        label="Period",
    )

    # Get date range from data
    # For end_date, use the date of the max datetime to ensure we include the last launch
    # (the date picker will default to end of day when converted)
    min_date = df_electron["Launch_Date_ET"].min().date()
    max_date = df_electron["Launch_Date_ET"].max().date()

    start_date_control = mo.ui.date(
        value=min_date,
        label="Start Date",
    )

    end_date_control = mo.ui.date(
        value=max_date,
        label="End Date",
    )

    mo.hstack([period_control, start_date_control, end_date_control])
    return end_date_control, period_control, start_date_control


@app.cell
def _(df_electron, end_date_control, period_control, start_date_control):
    # Use the interactive controls to filter and aggregate
    df_aggregated = cumulative_launches_by_period(
        df_electron,
        period=period_control.value,
        start_date=start_date_control.value,
        end_date=end_date_control.value,
    )
    return (df_aggregated,)


@app.cell
def _(df_aggregated, period_control):
    import launch_charts

    chart = launch_charts.create_cumulative_launches_chart(df_aggregated, period=period_control.value)
    chart_log = launch_charts.create_cumulative_launches_chart_log(df_aggregated, period=period_control.value)

    mo.hstack(
        [chart, chart_log],
        widths=[1, 1],
        wrap=True,
        gap=1.5,
    )
    return


@app.cell
def _(df_aggregated):
    df_aggregated.sort_values("date", ascending=False).set_index("period_label")
    return


@app.cell
def _(df_electron):
    df_electron[["Flight_ID", "Flight", "Launch_Date_ET"]].sort_values("Launch_Date_ET", ascending=False).set_index("Flight_ID")
    return


@app.cell
def _():
    mo.md("""
    **Data Citation:**

    McDowell, Jonathan C., 2020. General Catalog of Artificial Space Objects,
    Release 1.8.0, https://planet4589.org/space/gcat
    """)
    return


@app.cell
def _():
    # GoFundMe widget embed - using iframe
    mo.Html("""
    <div style="margin-top: 50px;">
    <iframe 
        src="https://www.gofundme.com/f/fund-jonathans-space-report-library-transition/widget/medium" 
        width="100%" 
        height="315" 
        style="border: none; max-width: 100%;">
    </iframe>
    </div>
    """)
    return


@app.function
def parse_vague_dates_to_eastern(
    date_series, tz="America/New_York", output_type="date"
):
    """Parse Vague Date format strings and convert to specified timezone.

    Wrapper around the parser module for use in marimo notebooks.

    Args:
        date_series: pandas Series of Vague Date format strings
        tz: Timezone to convert to (default: 'America/New_York')
        output_type: 'datetime' or 'date' (default: 'date')
    """
    import vague_date_parser

    return vague_date_parser.parse_vague_dates_to_eastern(date_series, tz, output_type)


@app.function
def load_electron_data(filepath: str = "data/raw/Electron.tsv"):
    """Load Electron launch data from TSV file.

    Args:
        filepath: Path to the Electron.tsv file (local or URL)

    Returns:
        DataFrame with Electron launch data
    """
    # Try local file access first (for development)
    try:
        with open(filepath, "r") as file:
            # Read first line to get headers
            first_line = file.readline()
            header_line = first_line.lstrip("#").strip()
            headers = [h.strip() for h in header_line.split("\t")]
            # Filter out empty headers (in case of trailing tabs)
            headers = [h for h in headers if h]

        df = pd.read_csv(
            filepath,
            dtype=str,
            names=headers,
            sep="\t",
            comment="#",  # Pandas handles this natively
            skipinitialspace=True,
        )
        
        # Verify that we got the expected columns
        if 'Launch_Date' not in df.columns:
            raise ValueError(
                f"Expected 'Launch_Date' column not found. "
                f"Available columns: {list(df.columns)}"
            )
        
        return df
    except (FileNotFoundError, OSError):
        # If local file access fails, try HTTP (for browser/WASM deployment)
        # Use the path that works in the deployed environment
        browser_filepath = "../data/raw/Electron.tsv"
        
        # Fetch file content - pandas in Pyodide doesn't support URLs directly
        # so we need to fetch and use StringIO
        from io import StringIO
        
        content = None
        fetch_error = None
        try:
            # Try Pyodide's http module (available in browser/WASM)
            import pyodide.http
            response = pyodide.http.open_url(browser_filepath)
            # Pyodide's open_url returns a file-like object
            content = response.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            elif hasattr(content, 'decode'):
                content = content.decode('utf-8')
        except Exception as e:
            fetch_error = e
            # Fallback to urllib
            try:
                import urllib.request
                with urllib.request.urlopen(browser_filepath) as response:
                    content = response.read().decode('utf-8')
            except Exception as e2:
                raise FileNotFoundError(
                    f"Could not load data file from {filepath} or {browser_filepath}. "
                    f"Pyodide error: {fetch_error}, "
                    f"urllib error: {e2}"
                )
        
        if not content or len(content.strip()) == 0:
            raise FileNotFoundError(
                f"Data file appears to be empty. Path: {browser_filepath}"
            )
        
        # Parse header from first line (which starts with #)
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = content.split('\n')
        
        # Find the first line that looks like a header
        header_line = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') and '\t' in stripped:
                header_line = stripped.lstrip("#").strip()
                break
        
        if not header_line:
            # Provide more helpful error message
            preview = content[:500] if content else "(empty content)"
            raise ValueError(
                f"Could not find header line in data file. "
                f"Path: {browser_filepath}, "
                f"Content preview (first 500 chars): {preview}, "
                f"Number of lines: {len(lines)}"
            )
        
        headers = [h.strip() for h in header_line.split("\t")]
        # Filter out empty headers (in case of trailing tabs)
        headers = [h for h in headers if h]
        
        # Read CSV from StringIO (pandas in Pyodide needs file-like object, not URL)
        df = pd.read_csv(
            StringIO(content),
            dtype=str,
            names=headers,
            sep="\t",
            comment="#",
            skipinitialspace=True,
        )
        
        # Verify that we got the expected columns
        if 'Launch_Date' not in df.columns:
            raise ValueError(
                f"Expected 'Launch_Date' column not found. "
                f"Available columns: {list(df.columns)}"
            )
        
        return df


@app.function
def cumulative_launches_by_period(
    df, period: str = "quarter", start_date=None, end_date=None
):
    """Aggregate launches by time period with cumulative counts.

    Wrapper around launch_aggregation module for use in marimo notebooks.

    Args:
        df: DataFrame with 'Launch_Date_ET' column (datetime)
        period: Time period to aggregate by ('month', 'quarter', or 'year')
        start_date: Optional start date to filter (inclusive). Can be string or datetime.
        end_date: Optional end date to filter (inclusive). Can be string or datetime.

    Returns:
        DataFrame with 'date', 'period_label', and 'launch_count' columns (cumulative total)
    """
    import launch_aggregation

    return launch_aggregation.cumulative_launches_by_period(
        df, period=period, start_date=start_date, end_date=end_date
    )


if __name__ == "__main__":
    app.run()
