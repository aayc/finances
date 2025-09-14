"""Account Balances view for OurFinance."""

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


def get_balance_history(entries: List, account_pattern: str, months: int = 12) -> pd.DataFrame:
    """Get balance history for an account or account pattern over time.

    Args:
        entries: List of beancount entries
        account_pattern: Account name or pattern (e.g., "Assets" or "Assets:US:Bank")
        months: Number of months of history to get

    Returns:
        DataFrame with date and balance columns
    """
    history = []
    end_date = datetime.now().date()

    for i in range(months):
        # Calculate date for each month
        month_date = end_date.replace(day=1) - timedelta(days=32*i)
        month_date = month_date.replace(day=1)  # First day of month

        try:
            # Get balances for this date
            balances = bc_utils.get_account_balances(entries, {}, month_date)

            # Filter accounts matching the pattern
            if account_pattern == "Assets":
                matching_balances = balances[balances["account"].str.startswith("Assets:")]
            elif account_pattern == "Liabilities":
                matching_balances = balances[balances["account"].str.startswith("Liabilities:")]
            elif account_pattern == "Income":
                matching_balances = balances[balances["account"].str.startswith("Income:")]
            elif account_pattern == "Expenses":
                matching_balances = balances[balances["account"].str.startswith("Expenses:")]
            else:
                # Exact match or prefix match
                matching_balances = balances[
                    balances["account"].str.startswith(account_pattern + ":") |
                    (balances["account"] == account_pattern)
                ]

            total_balance = matching_balances["amount"].sum() if len(matching_balances) > 0 else 0

            history.append({
                "date": month_date,
                "balance": total_balance,
                "month_name": month_date.strftime("%Y-%m")
            })

        except Exception:
            # If we can't get balance for this date, skip it
            continue

    # Sort by date
    history_df = pd.DataFrame(history)
    if len(history_df) > 0:
        history_df = history_df.sort_values("date")

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

        # Show balance history chart at the top
        st.subheader(f"📈 Balance History: {st.session_state.selected_account}")

        # Get and display balance history
        history_df = get_balance_history(entries, st.session_state.selected_account)

        if len(history_df) > 0:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=history_df["date"],
                y=history_df["balance"],
                mode='lines+markers',
                name=st.session_state.selected_account,
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))

            fig.update_layout(
                title=f"{st.session_state.selected_account} Balance Over Time",
                xaxis_title="Date",
                yaxis_title="Balance ($)",
                hovermode='x unified',
                height=400
            )

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