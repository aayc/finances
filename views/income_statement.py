"""Income Statement view for OurFinance."""

from typing import Dict, List, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import datetime

import beancount_utils as bc_utils
from views.common import (
    show_summary_metrics,
    show_dataframe_with_chart,
    show_error_with_details,
    show_no_data_message,
    create_trend_chart,
    get_account_category,
    clean_account_name
)


def show_budget_comparison(
    expense_df: pd.DataFrame,
    budget_data: Dict[str, Any],
    selected_year: int,
    selected_month: str,
    month_num: int
) -> None:
    """Display budget vs actual comparison.

    Args:
        expense_df: DataFrame with expense data
        budget_data: Dictionary with budget information
        selected_year: Selected year
        selected_month: Selected month name
        month_num: Selected month number
    """
    if month_num is None:
        return

    year_month_key = f"{selected_year}-{month_num:02d}"
    month_budgets = budget_data.get(year_month_key, {})

    if not month_budgets:
        st.info(f"No budget data found for {selected_month} {selected_year}")
        return

    # Create detailed expense breakdown by account
    expense_df_detailed = expense_df.copy()
    expense_df_detailed["amount"] = expense_df_detailed["amount"].abs()

    # Add budget information
    budget_comparison = []
    for _, row in expense_df_detailed.iterrows():
        account = row["account"]
        actual = row["amount"]

        # Look for budget for this account or parent accounts
        budget_amount = None
        budget_account = None

        # Check exact match first
        if account in month_budgets:
            budget_amount = month_budgets[account]["amount"]
            budget_account = account
        else:
            # Check parent accounts (e.g., Expenses:Food for Expenses:Food:Groceries)
            account_parts = account.split(":")
            for i in range(len(account_parts) - 1, 0, -1):
                parent_account = ":".join(account_parts[: i + 1])
                if parent_account in month_budgets:
                    budget_amount = month_budgets[parent_account]["amount"]
                    budget_account = parent_account
                    break

        difference = actual - (budget_amount or 0)

        budget_comparison.append({
            "account": clean_account_name(account),
            "full_account": account,  # Keep original for matching
            "category": get_account_category(account),
            "actual": actual,
            "budget": budget_amount or 0,
            "budget_account": budget_account,
            "difference": difference,
        })

    budget_df = pd.DataFrame(budget_comparison)

    # Show budget comparison table
    if not budget_df.empty and budget_df["budget"].sum() > 0:
        st.write(f"**Budget vs Actual for {selected_month} {selected_year}**")

        # Summary metrics
        total_budget = budget_df["budget"].sum()
        total_actual = budget_df["actual"].sum()
        total_difference = total_actual - total_budget

        show_summary_metrics([
            {
                "label": "Total Budgeted",
                "value": f"${total_budget:,.2f}"
            },
            {
                "label": "Total Actual",
                "value": f"${total_actual:,.2f}"
            },
            {
                "label": "Over/Under Budget",
                "value": f"${total_difference:,.2f}",
                "delta": f"${total_difference:+,.2f}" if total_difference != 0 else None
            }
        ])

        # Show all accounts, not just ones with budgets
        budget_display = budget_df.copy()
        budget_display = budget_display.sort_values("actual", ascending=False)

        # Replace zero budgets with N/A for display
        budget_display["budget_display"] = budget_display["budget"].apply(
            lambda x: "N/A" if x == 0 else f"${x:,.2f}"
        )

        # Replace difference with N/A for accounts without budgets
        budget_display["difference_display"] = budget_display.apply(
            lambda row: "N/A" if row["budget"] == 0 else f"${row['difference']:,.2f}",
            axis=1
        )

        # Add styling function for the difference column
        def style_difference(val):
            if val == "N/A" or pd.isna(val):
                return "color: gray; font-style: italic"
            try:
                # Extract numeric value from formatted string like "$123.45" or "-$123.45"
                numeric_val = float(val.replace("$", "").replace(",", ""))
                if numeric_val > 0:
                    return "color: red; font-weight: bold"  # Over budget
                elif numeric_val < 0:
                    return "color: green; font-weight: bold"  # Under budget
                else:
                    return ""  # Exactly on budget
            except:
                return ""

        # Create display dataframe
        display_data = {
            "Account": budget_display["account"],
            "Budgeted": budget_display["budget_display"],
            "Actual": budget_display["actual"].apply(lambda x: f"${x:,.2f}"),
            "Over/Under": budget_display["difference_display"]
        }

        display_df_final = pd.DataFrame(display_data)

        # Apply styling only to the Over/Under column
        styled_df = display_df_final.style.applymap(
            style_difference, subset=["Over/Under"]
        )

        st.dataframe(
            styled_df,
            hide_index=True,
            use_container_width=True,
        )

        # Budget difference chart
        if len(budget_display) > 0:
            fig_budget = px.bar(
                budget_display.head(10),  # Top 10 by difference
                x="difference",
                y="account",
                orientation="h",
                title="Budget vs Actual (Over/Under Budget)",
                labels={"difference": "Over/Under Budget ($)", "account": "Account"},
                color="difference",
                color_continuous_scale=["green", "white", "red"],
                color_continuous_midpoint=0,
            )
            fig_budget.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_budget, use_container_width=True)


def show_transactions_table(
    entries: List,
    options_map: Dict[str, Any],
    selected_year: int,
    month_num: int,
    income_df: pd.DataFrame,
    expense_df: pd.DataFrame
) -> None:
    """Display a filterable transactions table for the selected month.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
        selected_year: Selected year
        month_num: Selected month number
        income_df: Income DataFrame
        expense_df: Expense DataFrame
    """
    # Get all transactions for the month
    start_date = datetime(selected_year, month_num, 1).date()
    if month_num == 12:
        end_date = datetime(selected_year + 1, 1, 1).date()
    else:
        end_date = datetime(selected_year, month_num + 1, 1).date()

    all_transactions = bc_utils.get_transactions(
        entries, options_map,
        start_date=start_date,
        end_date=end_date
    )

    if len(all_transactions) == 0:
        st.info("No transactions found for this month.")
        return

    # Get unique accounts for filter
    all_accounts = ["All"] + sorted(all_transactions["account"].unique())

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        account_filter = st.selectbox(
            "Filter by Account",
            all_accounts,
            key="trans_account_filter"
        )

    with col2:
        sort_options = ["Date (Newest)", "Date (Oldest)", "Amount (High to Low)", "Amount (Low to High)"]
        sort_selection = st.selectbox("Sort by", sort_options, key="trans_sort")

    with col3:
        search_term = st.text_input("Search descriptions", key="trans_search")

    # Apply filters
    filtered_df = all_transactions.copy()

    if account_filter != "All":
        filtered_df = filtered_df[filtered_df["account"] == account_filter]

    if search_term:
        filtered_df = filtered_df[
            filtered_df["description"].str.contains(search_term, case=False, na=False)
        ]

    # Apply sorting
    if sort_selection == "Date (Newest)":
        filtered_df = filtered_df.sort_values("date", ascending=False)
    elif sort_selection == "Date (Oldest)":
        filtered_df = filtered_df.sort_values("date", ascending=True)
    elif sort_selection == "Amount (High to Low)":
        filtered_df = filtered_df.sort_values("amount", ascending=False, key=abs)
    elif sort_selection == "Amount (Low to High)":
        filtered_df = filtered_df.sort_values("amount", ascending=True, key=abs)

    if len(filtered_df) == 0:
        st.warning("No transactions match your filters.")
        return

    # Display results count
    st.write(f"Showing {len(filtered_df)} of {len(all_transactions)} transactions")

    # Format for display
    display_df = filtered_df.copy()
    display_df["account_clean"] = display_df["account"].apply(clean_account_name)
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


def show_income_statement(entries: List, options_map: Dict[str, Any]) -> None:
    """Display the income statement view with charts and analysis.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
    """
    st.header("📈 Income Statement")
    st.write("Income and expense analysis by month")

    # Date selection
    col1, col2 = st.columns(2)
    with col1:
        current_year = datetime.now().year
        selected_year = st.selectbox("Year", range(current_year - 2, current_year + 1), index=2)

    with col2:
        # Get months that have data for the selected year
        available_months = bc_utils.get_available_months_with_data(entries, selected_year)

        if available_months:
            # Create month options with only months that have data
            month_options = ["All"] + [calendar.month_name[i] for i in available_months]
            month_values = [None] + available_months

            # Default to current month if it has data, otherwise first available month
            current_month = datetime.now().month
            if current_month in available_months:
                default_index = available_months.index(current_month) + 1  # +1 for "All" option
            else:
                default_index = 1  # First month with data

            selected_month_idx = st.selectbox(
                "Month",
                range(len(month_options)),
                format_func=lambda x: month_options[x],
                index=default_index,
            )
            month_num = month_values[selected_month_idx]
            selected_month = month_options[selected_month_idx]
        else:
            st.warning(f"No transaction data found for {selected_year}")
            month_num = None
            selected_month = "All"

    try:
        # Get income and expense data
        income_df, expense_df = bc_utils.get_monthly_income_statement(
            entries, options_map, selected_year, month_num
        )

        if len(income_df) == 0 and len(expense_df) == 0:
            show_no_data_message(f"{selected_month} {selected_year}")
            return

        # Summary metrics
        total_income = income_df["amount"].sum() if len(income_df) > 0 else 0
        total_expenses = expense_df["amount"].sum() if len(expense_df) > 0 else 0
        net_income = abs(total_income) - abs(total_expenses)

        show_summary_metrics([
            {
                "label": "Total Income",
                "value": f"${abs(total_income):,.2f}"
            },
            {
                "label": "Total Expenses",
                "value": f"${abs(total_expenses):,.2f}"
            },
            {
                "label": "Net Income",
                "value": f"${net_income:,.2f}"
            }
        ])

        # Budget comparison (only for monthly view)
        if len(expense_df) > 0 and month_num is not None:
            st.subheader("📊 Monthly Expenses: Budget vs. Actual")

            # Get budget data
            budget_data = bc_utils.get_budget_data(entries, options_map)
            show_budget_comparison(expense_df, budget_data, selected_year, selected_month, month_num)

        # Income breakdown
        if len(income_df) > 0:
            st.subheader("💰 Monthly Income")

            # Format income data for display
            income_display = income_df.copy()
            income_display["amount"] = income_display["amount"].abs()
            income_display["account_clean"] = income_display["account"].apply(clean_account_name)
            income_display = income_display.sort_values("amount", ascending=False)

            st.dataframe(
                income_display[["account_clean", "amount"]],
                column_config={
                    "account_clean": "Income Source",
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                },
                hide_index=True,
                use_container_width=True,
            )

        # Monthly trends if viewing all months
        if selected_month == "All":
            st.subheader("📈 Monthly Trends")

            # Get monthly income and expense trends
            income_trends = bc_utils.get_monthly_trends(entries, options_map, "Income:", 12)
            expense_trends = bc_utils.get_monthly_trends(entries, options_map, "Expenses:", 12)

            if len(income_trends) > 0 or len(expense_trends) > 0:
                fig_trends = go.Figure()

                if len(income_trends) > 0:
                    fig_trends.add_trace(
                        go.Scatter(
                            x=income_trends["month_name"],
                            y=income_trends["amount"].abs(),
                            mode="lines+markers",
                            name="Income",
                            line=dict(color="green", width=3),
                            marker=dict(size=8),
                        )
                    )

                if len(expense_trends) > 0:
                    fig_trends.add_trace(
                        go.Scatter(
                            x=expense_trends["month_name"],
                            y=expense_trends["amount"].abs(),
                            mode="lines+markers",
                            name="Expenses",
                            line=dict(color="red", width=3),
                            marker=dict(size=8),
                        )
                    )

                fig_trends.update_layout(
                    title="Monthly Income vs Expenses",
                    xaxis_title="Month",
                    yaxis_title="Amount ($)",
                    hovermode="x unified",
                    height=400,
                )

                st.plotly_chart(fig_trends, use_container_width=True)

        # Transactions table (for specific month only)
        if month_num is not None:
            st.subheader("📋 Transactions")
            show_transactions_table(entries, options_map, selected_year, month_num, income_df, expense_df)

    except Exception as e:
        show_error_with_details("Error loading income statement data", e)