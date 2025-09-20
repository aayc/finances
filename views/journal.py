"""Transaction Journal view for OurFinance."""

from typing import Dict, List, Any
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
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

    # Add parent accounts (like "Assets", "Expenses", "Income", "Liabilities")
    parent_accounts = ["Assets", "Expenses", "Income", "Liabilities"]

    # Combine parent accounts with specific accounts
    account_options = ["All"] + parent_accounts + all_accounts

    # Check if parameters were passed via query parameters
    query_params = st.query_params
    preselected_account = query_params.get("account", None)
    preselected_month = query_params.get("month", None)  # Format: YYYY-MM
    preselected_account_type = query_params.get("account_type", None)  # "Expenses", "Income", etc.

    # Determine the initial account filter index
    initial_index = 0

    if preselected_account and preselected_account in account_options:
        try:
            initial_index = account_options.index(preselected_account)
        except ValueError:
            initial_index = 0
    elif preselected_account_type and preselected_account_type in account_options:
        # If account_type is specified (e.g., "Expenses"), select it directly
        try:
            initial_index = account_options.index(preselected_account_type)
        except ValueError:
            initial_index = 0

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        account_filter = st.selectbox("Filter by Account", account_options, index=initial_index)

        # Clear query parameters after they've been used to avoid persistence
        params_to_clear = []
        if preselected_account and "account" in st.query_params:
            params_to_clear.append("account")
        if preselected_month and "month" in st.query_params:
            params_to_clear.append("month")
        if preselected_account_type and "account_type" in st.query_params:
            params_to_clear.append("account_type")

        for param in params_to_clear:
            del st.query_params[param]

    with col2:
        # Set default start date based on preselected month or current year start
        if preselected_month:
            try:
                year, month = map(int, preselected_month.split("-"))
                default_start = datetime(year, month, 1).date()
            except ValueError:
                default_start = datetime.now().date().replace(month=1, day=1)
        else:
            default_start = datetime.now().date().replace(month=1, day=1)

        start_date = st.date_input("Start Date", value=default_start)

    with col3:
        # Set default end date based on preselected month or current date
        if preselected_month:
            try:
                year, month = map(int, preselected_month.split("-"))
                # Get last day of the month
                if month == 12:
                    default_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    default_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            except ValueError:
                default_end = datetime.now().date()
        else:
            default_end = datetime.now().date()

        end_date = st.date_input("End Date", value=default_end)

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