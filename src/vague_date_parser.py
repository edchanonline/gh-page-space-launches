"""Vague Date format parser.

Parses dates in the Vague Date format used by the JSR Launch Vehicle Database.
This module can be imported by both marimo notebooks and test files.
"""

import pandas as pd
from zoneinfo import ZoneInfo
from typing import Literal


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
