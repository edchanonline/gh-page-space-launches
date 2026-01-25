import marimo

__generated_with = "0.19.6"
app = marimo.App(width="full")

with app.setup(hide_code=True):
    import marimo as mo
    import pandas as pd
    import warnings
    from zoneinfo import ZoneInfo
    from typing import Literal
    import altair as alt
    
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
    chart = create_cumulative_launches_chart(df_aggregated, period=period_control.value)
    chart_log = create_cumulative_launches_chart_log(df_aggregated, period=period_control.value)

    # Toggle button: False = vstack (mobile-friendly), True = hstack
    layout_toggle = mo.ui.switch(
        value=False,  # Default to vstack for mobile
        label="Horizontal Layout",
    )
    layout_toggle
    return chart, chart_log, layout_toggle


@app.cell
def _(chart, chart_log, layout_toggle):
    # Conditionally render hstack or vstack based on toggle
    if layout_toggle.value:
        layout = mo.hstack(
            [chart, chart_log],
            widths=[1, 1],
            wrap=True,
            gap=1.5,
        )
    else:
        layout = mo.vstack(
            [chart, chart_log],
            gap=1.5,
        )
    
    layout
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
    date_series, 
    tz='America/New_York',
    output_type: Literal['datetime', 'date'] = 'date'
):
    """Parse Vague Date format strings and convert to specified timezone.

    Parses dates in the Vague Date format used by the JSR Launch Vehicle Database.
    Handles HMS format (hhmm:ss or hhmm) and date-only formats (YYYY MMM DD).

    Vague Date format specification:
    https://planet4589.org/space/gcat/web/intro/vague.html

    Args:
        date_series: pandas Series of Vague Date format strings (e.g., "2017 May 25 0420:00")
        tz: Timezone to convert to (default: 'America/New_York' for Eastern time).
            Can be any valid timezone string (e.g., 'UTC', 'Europe/London', 'Asia/Tokyo')
        output_type: 'datetime' for datetime objects, 'date' for date objects (default: 'date').
                     When 'date', converts to timezone first, then extracts date component.

    Returns:
        pandas Series of datetime or date objects in the specified timezone (default: date)
    """
    # Strip uncertainty markers and schedule flags (? and s)
    # The ? indicates uncertainty but we'll parse to the best precision available
    date_series_clean = date_series.str.rstrip('?s')

    # Try parsing with seconds format first (HMS format: hhmm:ss)
    dates = pd.to_datetime(date_series_clean, format='%Y %b %d %H%M:%S', errors='coerce')

    # For those that failed, try without seconds (HMS format: hhmm)
    mask = dates.isna()
    if mask.any():
        dates.loc[mask] = pd.to_datetime(
            date_series_clean.loc[mask], 
            format='%Y %b %d %H%M', 
            errors='coerce'
        )

    # For those that still failed, try date-only format (YYYY MMM DD)
    mask = dates.isna()
    if mask.any():
        dates.loc[mask] = pd.to_datetime(
            date_series_clean.loc[mask], 
            format='%Y %b %d', 
            errors='coerce'
        )

    # Convert UTC to specified timezone
    # First make timezone-aware as UTC (Vague Date format is always UTC)
    dates = dates.dt.tz_localize('UTC')
    # Then convert to requested timezone
    dates = dates.dt.tz_convert(tz)

    # If output_type is 'date', convert to date after timezone conversion
    if output_type == 'date':
        # Extract date component after timezone conversion
        dates = dates.dt.date

    return dates


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
        
        # Add cache-busting query parameter to force fresh loads
        # This prevents browsers from serving stale cached data
        import time
        cache_buster = f"?v={int(time.time())}"
        browser_filepath_with_cache = f"{browser_filepath}{cache_buster}"
        
        # Fetch file content - pandas in Pyodide doesn't support URLs directly
        # so we need to fetch and use StringIO
        from io import StringIO
        
        content = None
        fetch_error = None
        try:
            # Try Pyodide's http module (available in browser/WASM)
            import pyodide.http
            response = pyodide.http.open_url(browser_filepath_with_cache)
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
                with urllib.request.urlopen(browser_filepath_with_cache) as response:
                    content = response.read().decode('utf-8')
            except Exception as e2:
                raise FileNotFoundError(
                    f"Could not load data file from {filepath} or {browser_filepath_with_cache}. "
                    f"Pyodide error: {fetch_error}, "
                    f"urllib error: {e2}"
                )
        
        if not content or len(content.strip()) == 0:
            raise FileNotFoundError(
                f"Data file appears to be empty. Path: {browser_filepath_with_cache}"
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
                f"Path: {browser_filepath_with_cache}, "
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

    Args:
        df: DataFrame with 'Launch_Date_ET' column (datetime)
        period: Time period to aggregate by ('month', 'quarter', or 'year')
        start_date: Optional start date to filter (inclusive). Can be string or datetime.
        end_date: Optional end date to filter (inclusive). Can be string or datetime.

    Returns:
        DataFrame with 'date', 'period_label', and 'launch_count' columns (cumulative total)
    """
    # Ensure Launch_Date_ET is datetime
    df_period = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_period["Launch_Date_ET"]):
        df_period["Launch_Date_ET"] = pd.to_datetime(df_period["Launch_Date_ET"])

    # Filter by date range if provided
    if start_date is not None:
        start_date = pd.to_datetime(start_date)
        # If Launch_Date_ET is timezone-aware, localize start_date to same timezone
        if df_period["Launch_Date_ET"].dt.tz is not None:
            if start_date.tz is None:
                start_date = start_date.tz_localize(df_period["Launch_Date_ET"].dt.tz)
        df_period = df_period[df_period["Launch_Date_ET"] >= start_date]
    if end_date is not None:
        end_date = pd.to_datetime(end_date)
        # Set to end of day to be inclusive of all launches on that date
        # Normalize to start of day, add one day, then subtract 1 microsecond
        # This is more robust than setting 23:59:59 and handles timezone edge cases
        end_date = end_date.normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        # If Launch_Date_ET is timezone-aware, localize end_date to same timezone
        if df_period["Launch_Date_ET"].dt.tz is not None:
            if end_date.tz is None:
                end_date = end_date.tz_localize(df_period["Launch_Date_ET"].dt.tz)
        df_period = df_period[df_period["Launch_Date_ET"] <= end_date]

    # Map period string to pandas frequency
    period_map = {
        "month": "M",
        "quarter": "Q",
        "year": "Y",
    }

    if period not in period_map:
        raise ValueError(f"period must be one of {list(period_map.keys())}")

    # Group by period and count launches
    df_period["period"] = df_period["Launch_Date_ET"].dt.to_period(period_map[period])
    period_counts = df_period.groupby("period").size().reset_index(name="count")
    period_counts["date"] = period_counts["period"].dt.to_timestamp()
    period_counts = period_counts.sort_values("date")

    # Calculate cumulative sum
    period_counts["launch_count"] = period_counts["count"].cumsum()

    # Add label for period (e.g., "2018Q1", "2018-01", "2018")
    period_counts["period_label"] = period_counts["period"].astype(str)
    aggregated = period_counts[["date", "period_label", "launch_count"]]

    return aggregated


@app.function
def create_cumulative_launches_chart(df_aggregated: pd.DataFrame, period: str = "quarter") -> alt.Chart:
    """Create a basic line chart of cumulative launches over time.
    
    Args:
        df_aggregated: DataFrame from cumulative_launches_by_period() with columns:
                      'date', 'period_label', 'launch_count'
        period: Period string ('month', 'quarter', or 'year') for title display
    
    Returns:
        Altair Chart object
    """
    # Chart configuration
    CHART_CONFIG = {
        'width': 'container', 
        'height': 400,
    }
    
    # Convert period to display format
    period_display_map = {
        "month": "Monthly",
        "quarter": "Quarterly",
        "year": "Yearly",
    }
    period_display = period_display_map.get(period, "Quarterly")
    
    # Create main chart
    chart = (
        alt.Chart(df_aggregated)
        .mark_line(point=True)
        .encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('launch_count:Q', title='Cumulative Launch Count'),
            tooltip=[
                alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
                alt.Tooltip('period_label:N', title='Period'),
                alt.Tooltip('launch_count:Q', title='Cumulative Launches', format=',.0f'),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text=f'Cumulative Electron Launches ({period_display})',
                subtitle='talknewspace.com',
            ),
            **CHART_CONFIG,
        )
        .interactive()
    )
    
    return chart


@app.function
def create_cumulative_launches_chart_log(df_aggregated: pd.DataFrame, period: str = "quarter") -> alt.Chart:
    """Create a line chart of cumulative launches over time with log scale on y-axis.
    
    Args:
        df_aggregated: DataFrame from cumulative_launches_by_period() with columns:
                      'date', 'period_label', 'launch_count'
        period: Period string ('month', 'quarter', or 'year') for title display
    
    Returns:
        Altair Chart object with log scale y-axis
    """
    # Chart configuration
    CHART_CONFIG = {
        'width': 'container', 
        'height': 400,
    }
    
    # Convert period to display format
    period_display_map = {
        "month": "Monthly",
        "quarter": "Quarterly",
        "year": "Yearly",
    }
    period_display = period_display_map.get(period, "Quarterly")
    
    # Create main chart with log scale on y-axis
    chart = (
        alt.Chart(df_aggregated)
        .mark_line(point=True)
        .encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('launch_count:Q', title='Cumulative Launch Count (Log Scale)', 
                    scale=alt.Scale(type='log')),
            tooltip=[
                alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
                alt.Tooltip('period_label:N', title='Period'),
                alt.Tooltip('launch_count:Q', title='Cumulative Launches', format=',.0f'),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text=f'Cumulative Electron Launches - Log Scale ({period_display})',
                subtitle='talknewspace.com',
            ),
            **CHART_CONFIG,
        )
        .interactive()
    )
    
    return chart


if __name__ == "__main__":
    app.run()
