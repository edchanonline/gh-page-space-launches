"""Launch aggregation functions for space launch data analysis."""

import pandas as pd


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
