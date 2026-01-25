"""Chart creation functions for space launch data visualization."""

import pandas as pd
import altair as alt

CHART_CONFIG = {
    'width': 'container', 
    'height': 400,
}


def create_cumulative_launches_chart(df_aggregated: pd.DataFrame, period: str = "quarter") -> alt.Chart:
    """Create a basic line chart of cumulative launches over time.
    
    Args:
        df_aggregated: DataFrame from cumulative_launches_by_period() with columns:
                      'date', 'period_label', 'launch_count'
        period: Period string ('month', 'quarter', or 'year') for title display
    
    Returns:
        Altair Chart object
    """
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


def create_cumulative_launches_chart_log(df_aggregated: pd.DataFrame, period: str = "quarter") -> alt.Chart:
    """Create a line chart of cumulative launches over time with log scale on y-axis.
    
    Args:
        df_aggregated: DataFrame from cumulative_launches_by_period() with columns:
                      'date', 'period_label', 'launch_count'
        period: Period string ('month', 'quarter', or 'year') for title display
    
    Returns:
        Altair Chart object with log scale y-axis
    """
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
