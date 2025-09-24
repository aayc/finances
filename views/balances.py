"""Account Balances view for Finances."""

from typing import Dict, List, Any, Tuple
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import defaultdict

import beancount_utils as bc_utils
from views.common import (
    show_summary_metrics,
    show_error_with_details,
)


def build_account_tree(balances_df: pd.DataFrame) -> Dict:
    """Build a hierarchical tree structure from account balances.

    Args:
        balances_df: DataFrame with account balances

    Returns:
        Dictionary representing the account tree
    """
    tree = {}

    for _, row in balances_df.iterrows():
        account = row["account"]
        amount = row["amount"]

        # Split account into parts (e.g., "Assets:US:Bank:Checking" -> ["Assets", "US", "Bank", "Checking"])
        parts = account.split(":")

        # Navigate/create tree structure
        current = tree
        path = []

        for i, part in enumerate(parts):
            path.append(part)
            full_path = ":".join(path)

            if part not in current:
                current[part] = {
                    "_balance": 0.0,
                    "_full_path": full_path,
                    "_children": {},
                    "_is_leaf": i == len(parts) - 1
                }

            current[part]["_balance"] += amount
            current = current[part]["_children"]

    return tree


def format_currency_for_chart(value: float) -> str:
    """Format currency values for chart labels with K abbreviation.

    Args:
        value: The numeric value to format

    Returns:
        Formatted string like "$1.23K" or "$456.78"
    """
    if abs(value) >= 1000:
        return f"${value/1000:.2f}K"
    else:
        return f"${value:.2f}"


@st.cache_data
def _precompute_all_balances(_entries: List, months: int = 12) -> Dict[str, pd.DataFrame]:
    """Precompute balance histories for all major account types to improve performance.

    This function computes balance histories for all main account patterns in one pass,
    which is much more efficient than computing them separately.

    Args:
        _entries: List of beancount entries (prefixed with _ for caching)
        months: Number of months of history to get

    Returns:
        Dictionary mapping account patterns to their balance history DataFrames
    """
    from collections import defaultdict
    from beancount.core import data

    end_date = datetime.now().date()

    # Generate list of month dates we want to calculate
    month_dates = []
    for i in range(months):
        month_date = end_date.replace(day=1) - timedelta(days=32*i)
        month_date = month_date.replace(day=1)  # First day of month
        month_dates.append(month_date)

    # Sort dates chronologically for processing
    month_dates.sort()

    # Get all transaction entries and sort by date
    transactions = [entry for entry in _entries if isinstance(entry, data.Transaction)]
    transactions.sort(key=lambda x: x.date)

    # Track balances for all accounts
    all_balances = {}

    # Process all major account patterns
    patterns = ["Assets", "Liabilities", "Income", "Expenses"]

    # Add specific account patterns that might be requested
    specific_accounts = set()
    for transaction in transactions:
        for posting in transaction.postings:
            if posting.account:
                account_parts = posting.account.split(':')
                # Add patterns like "Assets:US", "Assets:US:Bank", etc.
                for i in range(2, len(account_parts) + 1):
                    specific_accounts.add(':'.join(account_parts[:i]))

    all_patterns = patterns + list(specific_accounts)

    for pattern in all_patterns:
        account_balances = defaultdict(float)
        history = []
        transaction_idx = 0

        for month_date in month_dates:
            # Process all transactions up to this month date
            while transaction_idx < len(transactions) and transactions[transaction_idx].date <= month_date:
                transaction = transactions[transaction_idx]

                for posting in transaction.postings:
                    if posting.account and posting.units:
                        account_matches = False

                        if pattern == "Assets":
                            account_matches = posting.account.startswith("Assets:")
                        elif pattern == "Liabilities":
                            account_matches = posting.account.startswith("Liabilities:")
                        elif pattern == "Income":
                            account_matches = posting.account.startswith("Income:")
                        elif pattern == "Expenses":
                            account_matches = posting.account.startswith("Expenses:")
                        else:
                            account_matches = (posting.account.startswith(pattern + ":") or
                                             posting.account == pattern)

                        if account_matches:
                            account_balances[posting.account] += float(posting.units.number)

                transaction_idx += 1

            # Calculate total balance for all matching accounts
            total_balance = sum(account_balances.values())

            history.append({
                "date": month_date,
                "balance": total_balance,
                "month_name": month_date.strftime("%Y-%m")
            })

        # Sort by date (reverse chronological for display)
        history_df = pd.DataFrame(history)
        if len(history_df) > 0:
            history_df = history_df.sort_values("date", ascending=False)

        all_balances[pattern] = history_df

    return all_balances


@st.cache_data
def get_monthly_transaction_totals(_entries: List, account_pattern: str, months: int = 12) -> pd.DataFrame:
    """Get monthly transaction totals for an account pattern (not cumulative).

    Each month shows only the sum of transactions that occurred in that specific month.

    Args:
        _entries: List of beancount entries (prefixed with _ for caching)
        account_pattern: Account name or pattern (e.g., "Assets" or "Assets:US:Bank")
        months: Number of months of history to get

    Returns:
        DataFrame with date and monthly_total columns
    """
    from collections import defaultdict
    from beancount.core import data
    from datetime import datetime, timedelta

    end_date = datetime.now().date()

    # Generate list of month dates we want to calculate
    month_dates = []
    for i in range(months):
        month_date = end_date.replace(day=1) - timedelta(days=32*i)
        month_date = month_date.replace(day=1)  # First day of month
        month_dates.append(month_date)

    # Sort dates chronologically for processing
    month_dates.sort()

    # Get all transaction entries and sort by date
    transactions = [entry for entry in _entries if isinstance(entry, data.Transaction)]
    transactions.sort(key=lambda x: x.date)

    # Find which accounts match our pattern
    def account_matches_pattern(account: str) -> bool:
        if account_pattern == "Assets":
            return account.startswith("Assets:")
        elif account_pattern == "Liabilities":
            return account.startswith("Liabilities:")
        elif account_pattern == "Income":
            return account.startswith("Income:")
        elif account_pattern == "Expenses":
            return account.startswith("Expenses:")
        else:
            return account.startswith(account_pattern + ":") or account == account_pattern

    history = []

    for i, month_date in enumerate(month_dates):
        # Calculate the end of this month
        if i < len(month_dates) - 1:
            next_month_date = month_dates[i + 1]
        else:
            # For the last month, use end of current month
            if month_date.month == 12:
                next_month_date = month_date.replace(year=month_date.year + 1, month=1)
            else:
                next_month_date = month_date.replace(month=month_date.month + 1)

        # Sum transactions that occurred only in this month
        monthly_total = 0.0

        for transaction in transactions:
            # Check if transaction is in this month
            if month_date <= transaction.date < next_month_date:
                for posting in transaction.postings:
                    if posting.account and posting.units and account_matches_pattern(posting.account):
                        monthly_total += float(posting.units.number)

        history.append({
            "date": month_date,
            "monthly_total": monthly_total,
            "month_name": month_date.strftime("%Y-%m")
        })

    # Sort by date (reverse chronological for display)
    history_df = pd.DataFrame(history)
    if len(history_df) > 0:
        history_df = history_df.sort_values("date", ascending=False)

    return history_df


@st.cache_data
def get_balance_history(_entries: List, account_pattern: str, months: int = 12) -> pd.DataFrame:
    """Get balance history for an account or account pattern over time.

    Optimized version that uses precomputed balance data when possible.

    Args:
        _entries: List of beancount entries (prefixed with _ for caching)
        account_pattern: Account name or pattern (e.g., "Assets" or "Assets:US:Bank")
        months: Number of months of history to get

    Returns:
        DataFrame with date and balance columns
    """
    # Try to use precomputed data first
    try:
        all_balances = _precompute_all_balances(_entries, months)
        if account_pattern in all_balances:
            return all_balances[account_pattern]
    except Exception:
        # Fall back to individual calculation if precomputation fails
        pass

    # Fallback: compute individual balance history
    from collections import defaultdict
    from beancount.core import data

    end_date = datetime.now().date()

    # Generate list of month dates we want to calculate
    month_dates = []
    for i in range(months):
        month_date = end_date.replace(day=1) - timedelta(days=32*i)
        month_date = month_date.replace(day=1)  # First day of month
        month_dates.append(month_date)

    # Sort dates chronologically for processing
    month_dates.sort()

    # Track running balances per account
    account_balances = defaultdict(float)
    history = []

    # Get all transaction entries and sort by date
    transactions = [entry for entry in _entries if isinstance(entry, data.Transaction)]
    transactions.sort(key=lambda x: x.date)

    # Find which accounts match our pattern
    def account_matches_pattern(account: str) -> bool:
        if account_pattern == "Assets":
            return account.startswith("Assets:")
        elif account_pattern == "Liabilities":
            return account.startswith("Liabilities:")
        elif account_pattern == "Income":
            return account.startswith("Income:")
        elif account_pattern == "Expenses":
            return account.startswith("Expenses:")
        else:
            return account.startswith(account_pattern + ":") or account == account_pattern

    # Process transactions chronologically
    transaction_idx = 0

    for month_date in month_dates:
        # Process all transactions up to this month date
        while transaction_idx < len(transactions) and transactions[transaction_idx].date <= month_date:
            transaction = transactions[transaction_idx]

            for posting in transaction.postings:
                if posting.account and posting.units and account_matches_pattern(posting.account):
                    # Update running balance for this account
                    account_balances[posting.account] += float(posting.units.number)

            transaction_idx += 1

        # Calculate total balance for all matching accounts
        total_balance = sum(account_balances.values())

        history.append({
            "date": month_date,
            "balance": total_balance,
            "month_name": month_date.strftime("%Y-%m")
        })

    # Sort by date (reverse chronological for display)
    history_df = pd.DataFrame(history)
    if len(history_df) > 0:
        history_df = history_df.sort_values("date", ascending=False)

    return history_df


def render_account_tree(tree: Dict, level: int = 0, prefix: str = "") -> str:
    """Render the account tree structure with collapsible sections.

    Args:
        tree: Account tree dictionary
        level: Current indentation level
        prefix: Account path prefix

    Returns:
        Selected account path or None
    """
    selected_account = None

    for account_name, account_data in tree.items():
        if account_name.startswith("_"):
            continue

        balance = account_data["_balance"]
        full_path = account_data["_full_path"]
        children = account_data["_children"]

        # Create indentation
        indent = "　" * level  # Using wide space for better alignment

        # Determine if this has children
        has_children = len(children) > 0

        # Create expandable section for parent nodes
        if has_children:
            with st.expander(f"{indent}📁 {account_name}: ${balance:,.2f}", expanded=(level == 0)):
                # Add button to select this node for chart
                if st.button(f"📈 Show chart for {account_name}", key=f"chart_{full_path}"):
                    selected_account = full_path

                # Recursively render children
                child_selected = render_account_tree(children, level + 1, full_path)
                if child_selected:
                    selected_account = child_selected
        else:
            # Leaf node - just show as text with button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"{indent}📄 {account_name}: ${balance:,.2f}")
            with col2:
                if st.button("📈", key=f"chart_{full_path}", help=f"Show chart for {account_name}"):
                    selected_account = full_path

    return selected_account


def show_balances(entries: List, options_map: Dict[str, Any]) -> None:
    """Display the account balances view with hierarchical tree and charts.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
    """
    st.header("⚖️ Account Balances")
    st.write("Hierarchical view of all account balances")

    # Date selection for balance as of date
    as_of_date = st.date_input("Balance as of", value=datetime.now().date())

    try:
        # Get account balances
        balances_df = bc_utils.get_account_balances(entries, options_map, as_of_date)

        if len(balances_df) == 0:
            st.warning("No balance data found.")
            return

        # Filter out zero balances for tree display
        balances_df = balances_df[balances_df["amount"] != 0]

        # Build account tree
        account_tree = build_account_tree(balances_df)

        # Initialize selected account in session state
        if "selected_account" not in st.session_state:
            st.session_state.selected_account = "Assets"

        # Get list of available accounts for dropdown
        # Include major account categories plus specific accounts from the tree
        account_options = ["Assets", "Liabilities", "Income", "Expenses"]

        # Add specific accounts from the account tree
        def collect_account_paths(tree, prefix=""):
            paths = []
            for account_name, account_data in tree.items():
                if account_name.startswith("_"):
                    continue
                full_path = account_data["_full_path"]
                paths.append(full_path)
                # Recursively collect children
                children_paths = collect_account_paths(account_data["_children"])
                paths.extend(children_paths)
            return paths

        specific_accounts = collect_account_paths(account_tree)
        all_accounts = account_options + sorted(list(set(specific_accounts)))

        # Show balance history chart at the top
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            st.subheader("📈 Balance History")
        with col2:
            # Account selection dropdown
            current_account = st.session_state.selected_account
            if current_account not in all_accounts:
                # If current account is not in the list, add it
                all_accounts.insert(0, current_account)

            account_index = all_accounts.index(current_account) if current_account in all_accounts else 0
            selected_account = st.selectbox(
                "Account",
                all_accounts,
                index=account_index,
                key="account_selector"
            )

            # Update session state if account changed
            if selected_account != st.session_state.selected_account:
                st.session_state.selected_account = selected_account
                st.rerun()

        with col3:
            chart_type = st.selectbox(
                "Chart Type",
                ["Cumulative", "Monthly Change", "Monthly Totals"],
                key="balance_chart_type"
            )

        with col4:
            # Add some spacing and the button
            st.write("")  # Add vertical space to align with other elements
            if st.button("📔 See transactions", key="see_transactions_btn", help="View transactions for this account"):
                # Set query parameters to navigate to Journal page with this account preselected
                st.query_params.page = "Journal"
                st.query_params.account = st.session_state.selected_account
                st.rerun()

        # Get and display balance history
        with st.spinner("Crunching the numbers, just for you"):
            history_df = get_balance_history(entries, st.session_state.selected_account)

        if len(history_df) > 0:
            fig = go.Figure()

            if chart_type == "Cumulative":
                # Show cumulative balance over time
                fig.add_trace(go.Scatter(
                    x=history_df["date"],
                    y=history_df["balance"],
                    mode='lines+markers',
                    name=st.session_state.selected_account,
                    line=dict(color='blue', width=3),
                    marker=dict(size=8)
                ))

                fig.update_layout(
                    title=f"{st.session_state.selected_account} - Cumulative Balance",
                    xaxis_title="Date",
                    yaxis_title="Balance ($)",
                    hovermode='x unified',
                    height=400,
                    yaxis=dict(
                        tickformat='$,.0f',
                        tickmode='auto'
                    )
                )

                # Update hover template to show currency format
                fig.update_traces(
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                  'Date: %{x}<br>' +
                                  'Balance: $%{y:,.2f}<extra></extra>'
                )

            elif chart_type == "Monthly Change":
                # Calculate month-to-month changes
                history_sorted = history_df.sort_values("date")
                history_sorted["monthly_change"] = history_sorted["balance"].diff()

                # Remove the first row since it has NaN for change
                change_df = history_sorted.dropna()

                if len(change_df) > 0:
                    # Create bar chart for monthly changes
                    colors = ['green' if x >= 0 else 'red' for x in change_df["monthly_change"]]

                    fig.add_trace(go.Bar(
                        x=change_df["date"],
                        y=change_df["monthly_change"],
                        name="Monthly Change",
                        marker_color=colors
                    ))

                    fig.update_layout(
                        title=f"{st.session_state.selected_account} - Monthly Changes",
                        xaxis_title="Date",
                        yaxis_title="Change ($)",
                        hovermode='x unified',
                        height=400,
                        yaxis=dict(
                            tickformat='$,.0f',
                            tickmode='auto'
                        )
                    )

                    # Update hover template for bar chart
                    fig.update_traces(
                        hovertemplate='<b>Monthly Change</b><br>' +
                                      'Date: %{x}<br>' +
                                      'Change: $%{y:,.2f}<extra></extra>'
                    )

                    # Add zero line for reference
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

            else:  # Monthly Totals
                # Get monthly transaction totals (non-cumulative)
                monthly_df = get_monthly_transaction_totals(entries, st.session_state.selected_account)

                if len(monthly_df) > 0:
                    # Show monthly transaction totals as bar chart
                    colors = ['lightblue'] * len(monthly_df)

                    fig.add_trace(go.Bar(
                        x=monthly_df["date"],
                        y=monthly_df["monthly_total"],
                        name="Monthly Total",
                        marker_color=colors
                    ))

                    fig.update_layout(
                        title=f"{st.session_state.selected_account} - Monthly Transaction Totals",
                        xaxis_title="Date",
                        yaxis_title="Monthly Total ($)",
                        hovermode='x unified',
                        height=400,
                        yaxis=dict(
                            tickformat='$,.0f',
                            tickmode='auto'
                        )
                    )

                    # Update hover template for bar chart
                    fig.update_traces(
                        hovertemplate='<b>Monthly Total</b><br>' +
                                      'Date: %{x}<br>' +
                                      'Total: $%{y:,.2f}<extra></extra>'
                    )
                else:
                    st.info("No monthly transaction data available for this account.")

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No balance history available for this account.")

        # Show account tree
        st.subheader("🌳 Account Tree")
        st.write("Click on any account name to see its balance history chart above.")

        # Render the tree and get any selected account
        selected = render_account_tree(account_tree)

        # Update selected account if user clicked on one
        if selected:
            st.session_state.selected_account = selected
            st.rerun()  # Refresh to show new chart

        # Show summary metrics at the bottom
        st.subheader("📊 Summary")

        assets = balances_df[balances_df["account"].str.startswith("Assets:")]["amount"].sum()
        liabilities = balances_df[balances_df["account"].str.startswith("Liabilities:")]["amount"].sum()
        net_worth = assets + liabilities

        show_summary_metrics([
            {
                "label": "Total Assets",
                "value": f"${assets:,.2f}"
            },
            {
                "label": "Total Liabilities",
                "value": f"${abs(liabilities):,.2f}"
            },
            {
                "label": "Net Worth",
                "value": f"${net_worth:,.2f}"
            }
        ])

    except Exception as e:
        show_error_with_details("Error loading balance data", e)