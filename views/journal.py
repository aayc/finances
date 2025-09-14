"""Transaction Journal view for OurFinance."""

from typing import Dict, List, Any
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from beancount.core import getters

import beancount_utils as bc_utils
from views.common import (
    show_summary_metrics,
    show_error_with_details,
    create_trend_chart,
    clean_account_name
)


def show_journal(entries: List, options_map: Dict[str, Any]) -> None:
    """Display the transaction journal view with filtering capabilities.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
    """
    st.header("📔 Transaction Journal")
    st.write("View and filter transactions by account")

    # Get all accounts for the filter
    all_accounts = sorted(getters.get_accounts(entries))

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        account_filter = st.selectbox("Filter by Account", ["All"] + all_accounts, index=0)

    with col2:
        start_date = st.date_input(
            "Start Date", value=datetime.now().date().replace(month=1, day=1)
        )

    with col3:
        end_date = st.date_input("End Date", value=datetime.now().date())

    # Additional filters
    col4, col5 = st.columns(2)

    with col4:
        min_amount = st.number_input("Minimum Amount ($)", value=0.0, step=0.01)

    with col5:
        search_description = st.text_input("Search Description")

    try:
        # Get transaction data
        account_filter_param = None if account_filter == "All" else account_filter

        transactions_df = bc_utils.get_transactions(
            entries,
            options_map,
            account_filter=account_filter_param,
            start_date=start_date,
            end_date=end_date,
        )

        if len(transactions_df) == 0:
            st.warning("No transactions found for the selected filters.")
            return

        # Apply additional filters
        if min_amount > 0:
            transactions_df = transactions_df[transactions_df["amount"].abs() >= min_amount]

        if search_description:
            transactions_df = transactions_df[
                transactions_df["description"].str.contains(
                    search_description, case=False, na=False
                )
            ]

        if len(transactions_df) == 0:
            st.warning("No transactions match your filters.")
            return

        # Summary statistics
        st.subheader("Transaction Summary")

        total_transactions = len(transactions_df)
        total_inflow = transactions_df[transactions_df["amount"] > 0]["amount"].sum()
        total_outflow = abs(transactions_df[transactions_df["amount"] < 0]["amount"].sum())
        net_amount = total_inflow - total_outflow

        show_summary_metrics([
            {
                "label": "Total Transactions",
                "value": f"{total_transactions:,}"
            },
            {
                "label": "Total Inflow",
                "value": f"${total_inflow:,.2f}"
            },
            {
                "label": "Total Outflow",
                "value": f"${total_outflow:,.2f}"
            },
            {
                "label": "Net Amount",
                "value": f"${net_amount:,.2f}"
            }
        ])

        # Transaction table
        st.subheader("Transactions")

        # Format the dataframe for display
        display_df = transactions_df.copy()
        display_df = display_df.sort_values("date", ascending=False)

        # Create a clean account display
        display_df["account_clean"] = display_df["account"].apply(clean_account_name)

        # Format dates
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")

        st.dataframe(
            display_df[["date", "account_clean", "description", "amount", "currency"]],
            column_config={
                "date": st.column_config.TextColumn("Date", width="small"),
                "account_clean": st.column_config.TextColumn("Account", width="medium"),
                "description": st.column_config.TextColumn("Description", width="large"),
                "amount": st.column_config.NumberColumn("Amount", format="$%.2f", width="small"),
                "currency": st.column_config.TextColumn("Currency", width="small"),
            },
            hide_index=True,
            use_container_width=True,
            height=400,
        )

        # Transaction trends
        if len(transactions_df) > 1:
            st.subheader("Transaction Trends")

            # Daily transaction amounts
            daily_df = transactions_df.copy()
            daily_df["date"] = pd.to_datetime(daily_df["date"])
            daily_summary = daily_df.groupby(daily_df["date"].dt.date)["amount"].sum().reset_index()

            if len(daily_summary) > 1:
                fig_daily = create_trend_chart(
                    daily_summary,
                    "date",
                    "amount",
                    "Daily Transaction Flow",
                    "blue",
                    "Date",
                    "Net Amount ($)"
                )
                st.plotly_chart(fig_daily, use_container_width=True)

        # Account breakdown (if showing all accounts)
        if account_filter == "All":
            st.subheader("Transactions by Account")

            account_summary = (
                transactions_df.groupby("account")
                .agg({"amount": ["count", "sum"], "date": ["min", "max"]})
                .round(2)
            )

            account_summary.columns = [
                "Transaction Count",
                "Total Amount",
                "First Transaction",
                "Last Transaction",
            ]
            account_summary = account_summary.sort_values("Total Amount", key=abs, ascending=False)

            st.dataframe(
                account_summary,
                column_config={
                    "Transaction Count": st.column_config.NumberColumn("Count"),
                    "Total Amount": st.column_config.NumberColumn("Total ($)", format="$%.2f"),
                    "First Transaction": st.column_config.TextColumn("First"),
                    "Last Transaction": st.column_config.TextColumn("Last"),
                },
                use_container_width=True,
            )

    except Exception as e:
        show_error_with_details("Error loading journal data", e)