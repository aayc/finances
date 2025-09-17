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
        # Get grouped transaction data (one row per transaction entry)
        account_filter_param = None if account_filter == "All" else account_filter

        transactions_df = bc_utils.get_grouped_transactions(
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

        # Transaction table
        st.subheader("Transactions")

        # Format the dataframe for display
        display_df = transactions_df.copy()
        display_df = display_df.sort_values("date", ascending=False)

        # Clean up account names for display
        display_df["accounts_clean"] = display_df["accounts"].apply(
            lambda x: " → ".join([clean_account_name(acc.strip()) for acc in x.split(" → ")]) if " → " in x else clean_account_name(x.replace(" (+more)", "").replace(" (+", " (+"))
        )

        # Format dates
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")

        # Add payee if available
        columns_to_show = ["date", "accounts_clean", "description", "amount", "currency"]
        column_config = {
            "date": st.column_config.TextColumn("Date", width="small"),
            "accounts_clean": st.column_config.TextColumn("Accounts", width="large"),
            "description": st.column_config.TextColumn("Description", width="large"),
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f", width="medium"),
            "currency": st.column_config.TextColumn("Curr", width="small"),
        }

        # Add payee column if any transactions have payee info
        if display_df["payee"].notna().any() and display_df["payee"].str.strip().str.len().sum() > 0:
            columns_to_show.insert(-2, "payee")  # Insert before amount and currency
            column_config["payee"] = st.column_config.TextColumn("Payee", width="medium")

        st.dataframe(
            display_df[columns_to_show],
            column_config=column_config,
            hide_index=True,
            use_container_width=True,
            height=400,
        )


    except Exception as e:
        show_error_with_details("Error loading journal data", e)