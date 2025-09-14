"""Common utilities and components shared across views."""

from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def show_summary_metrics(metrics: List[Dict[str, Any]]) -> None:
    """Display summary metrics in columns.

    Args:
        metrics: List of dicts with 'label', 'value', and optional 'delta' keys
    """
    cols = st.columns(len(metrics))
    for i, metric in enumerate(metrics):
        with cols[i]:
            st.metric(metric["label"], metric["value"], delta=metric.get("delta"))


def show_dataframe_with_chart(
    df: pd.DataFrame,
    value_col: str,
    name_col: str,
    title: str,
    chart_type: str = "pie",
    color_scheme: str = "Set3",
) -> None:
    """Display a dataframe alongside a chart.

    Args:
        df: DataFrame to display
        value_col: Column name for values
        name_col: Column name for labels
        title: Chart title
        chart_type: Type of chart ('pie', 'bar')
        color_scheme: Plotly color scheme
    """
    if df.empty:
        st.info("No data to display")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.dataframe(
            df.sort_values(value_col, ascending=False),
            column_config={
                name_col: name_col.replace("_", " ").title(),
                value_col: st.column_config.NumberColumn("Amount", format="$%.2f"),
            },
            hide_index=True,
            use_container_width=True,
        )

    with col2:
        if len(df) > 0:
            if chart_type == "pie":
                fig = px.pie(
                    df,
                    values=value_col,
                    names=name_col,
                    title=title,
                    color_discrete_sequence=getattr(
                        px.colors.qualitative, color_scheme
                    ),
                )
            elif chart_type == "bar":
                fig = px.bar(
                    df,
                    x=value_col,
                    y=name_col,
                    orientation="h",
                    title=title,
                    color_discrete_sequence=getattr(
                        px.colors.qualitative, color_scheme
                    ),
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})

            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def show_error_with_details(error_msg: str, exception: Exception) -> None:
    """Display error message with expandable details.

    Args:
        error_msg: User-friendly error message
        exception: Exception object for technical details
    """
    st.error(error_msg)
    with st.expander("View detailed error information"):
        st.exception(exception)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string.

    Args:
        amount: Numeric amount
        currency: Currency code

    Returns:
        Formatted currency string
    """
    return f"${amount:,.2f}" if currency == "USD" else f"{amount:,.2f} {currency}"


def get_account_category(account: str) -> str:
    """Extract category from account name.

    Args:
        account: Full account name like "Expenses:Food:Groceries"

    Returns:
        Category name like "Food"
    """
    parts = account.split(":")
    return parts[1] if len(parts) > 1 else account


def clean_account_name(account_name: str) -> str:
    """Remove common prefixes from account names for display.

    Removes prefixes like Expenses, Assets, Joint, Aaron, Mikayla to show
    just the meaningful part of the account name.

    Args:
        account_name: Full account name like "Expenses:Joint:Dining"

    Returns:
        Clean account name like "Dining"
    """
    if not account_name:
        return account_name

    parts = account_name.split(":")
    # Remove common prefixes
    filtered_parts = []
    for part in parts:
        if part not in [
            "Expenses",
            "Assets",
            "Income",
            "Liabilities",
            "Equity",
            "Joint",
        ]:
            filtered_parts.append(part)

    # Return the remaining parts joined, or the last part if nothing left
    if filtered_parts:
        return ":".join(filtered_parts)
    else:
        return parts[-1] if parts else account_name


def create_trend_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    line_color: str = "blue",
    x_label: str = "Date",
    y_label: str = "Amount ($)",
) -> go.Figure:
    """Create a trend line chart.

    Args:
        df: DataFrame with trend data
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        line_color: Color for the line
        x_label: X-axis label
        y_label: Y-axis label

    Returns:
        Plotly figure
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode="lines+markers",
            name=title,
            line=dict(color=line_color, width=3),
            marker=dict(size=8),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        hovermode="x unified",
        height=400,
    )

    return fig


def show_no_data_message(period: str = "") -> None:
    """Display a consistent no data message.

    Args:
        period: Optional period description
    """
    message = f"No data found{f' for {period}' if period else ''}."
    st.warning(message)
    st.info(
        "Try selecting a different time period or check if your beancount file has transactions for this period."
    )
