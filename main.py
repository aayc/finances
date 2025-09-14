import calendar
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from beancount import loader
from beancount.core import data, getters
from beancount.core.number import D

import beancount_utils as bc_utils

st.set_page_config(
    page_title="OurFinance", page_icon="💰", layout="wide", initial_sidebar_state="expanded"
)


# Load custom CSS
def load_css() -> None:
    """Load custom CSS styling for the application."""
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


try:
    load_css()
except FileNotFoundError:
    pass  # CSS file not found, continue without custom styling

# Configuration
BEANCOUNT_FILE: str = "/Users/aaronchan/Projects/Aaron Chan Vault/Ledgers/2025.beancount"

# UI Constants
PAGE_TITLES = {
    "Income Statement": "📈 Income Statement",
    "Balances": "⚖️ Account Balances",
    "Journal": "📔 Transaction Journal",
    "Forecast": "🔮 Financial Forecast",
    "Accounts": "🏦 Account Information",
}

PAGE_DESCRIPTIONS = {
    "Income Statement": "View your monthly income and expenses with interactive charts.",
    "Balances": "Check current balances across all your accounts.",
    "Journal": "Browse and filter your transaction history.",
    "Forecast": "Run what-if scenarios for major financial decisions.",
    "Accounts": "Access detailed information about all your accounts.",
}


@st.cache_data
def load_beancount_data() -> Tuple[List[data.Directive], List[Any], Dict[str, Any]]:
    """Load and parse the beancount file.

    Returns:
        Tuple of (entries, errors, options_map)
    """
    try:
        if not os.path.exists(BEANCOUNT_FILE):
            st.error(f"Beancount file not found: {BEANCOUNT_FILE}")
            st.info(
                "Please update the BEANCOUNT_FILE path in main.py to point to your ledger file."
            )
            return [], [], {}

        entries, errors, options_map = loader.load_file(BEANCOUNT_FILE)

        if errors:
            st.warning(f"Found {len(errors)} warnings/errors in beancount file:")
            for error in errors[:5]:  # Show first 5 errors
                st.warning(f"- {error}")
            if len(errors) > 5:
                st.warning(f"... and {len(errors) - 5} more errors")

        return entries, errors, options_map

    except FileNotFoundError:
        st.error(f"Beancount file not found: {BEANCOUNT_FILE}")
        st.info("Please update the BEANCOUNT_FILE path in main.py to point to your ledger file.")
        return [], [], {}

    except Exception as e:
        st.error(f"Failed to load beancount file: {str(e)}")
        st.exception(e)
        return [], [], {}


def main() -> None:
    """Main application entry point."""
    # Custom header with styling
    st.markdown(
        """
    <div class="main-header">
        <h1>💰 OurFinance</h1>
        <p>Your Personal Finance Dashboard</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Sidebar navigation with better styling
    st.sidebar.markdown("## 📊 Navigation")
    st.sidebar.markdown("Choose a view to explore your finances:")

    pages = list(PAGE_TITLES.keys())
    page = st.sidebar.selectbox("Select View:", pages, format_func=lambda x: PAGE_TITLES[x])

    # Add helpful sidebar information
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💡 Quick Tips")
    st.sidebar.info(PAGE_DESCRIPTIONS[page])

    # Load data
    entries, errors, options_map = load_beancount_data()

    if not entries:
        st.error(
            "No data loaded. Please check the beancount file path and ensure it contains valid transactions."
        )
        st.stop()  # Stop execution instead of return for better UX

    # Route to different pages
    if page == "Income Statement":
        show_income_statement(entries, options_map)
    elif page == "Balances":
        show_balances(entries, options_map)
    elif page == "Journal":
        show_journal(entries, options_map)
    elif page == "Forecast":
        show_forecast(entries, options_map)
    elif page == "Accounts":
        show_accounts()


def show_income_statement(entries: List[data.Directive], options_map: Dict[str, Any]) -> None:
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
        month_options = ["All"] + [calendar.month_name[i] for i in range(1, 13)]
        selected_month = st.selectbox("Month", month_options)

    month_num = None if selected_month == "All" else month_options.index(selected_month)

    try:
        # Get income and expense data
        income_df, expense_df = bc_utils.get_monthly_income_statement(
            entries, options_map, selected_year, month_num
        )

        if len(income_df) == 0 and len(expense_df) == 0:
            st.warning(f"No income or expense data found for {selected_month} {selected_year}.")
            st.info(
                "Try selecting a different time period or check if your beancount file has transactions for this period."
            )
            return

        # Summary metrics
        col1, col2, col3 = st.columns(3)

        total_income = income_df["amount"].sum() if len(income_df) > 0 else 0
        total_expenses = expense_df["amount"].sum() if len(expense_df) > 0 else 0
        net_income = abs(total_income) - abs(total_expenses)

        with col1:
            st.metric("Total Income", f"${abs(total_income):,.2f}", delta=None)

        with col2:
            st.metric("Total Expenses", f"${abs(total_expenses):,.2f}", delta=None)

        with col3:
            delta_color = "normal" if net_income >= 0 else "inverse"
            st.metric("Net Income", f"${net_income:,.2f}", delta=None)

        # Income breakdown
        if len(income_df) > 0:
            st.subheader("Income Breakdown")

            # Group by top-level account category
            income_df["category"] = income_df["account"].str.split(":").str[1]
            income_summary = income_df.groupby("category")["amount"].sum().reset_index()
            income_summary["amount"] = income_summary["amount"].abs()

            col1, col2 = st.columns(2)

            with col1:
                st.dataframe(
                    income_summary.sort_values("amount", ascending=False),
                    column_config={
                        "category": "Income Category",
                        "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    },
                    hide_index=True,
                )

            with col2:
                if len(income_summary) > 0:
                    fig_income = px.pie(
                        income_summary,
                        values="amount",
                        names="category",
                        title="Income Distribution",
                        color_discrete_sequence=px.colors.qualitative.Set3,
                    )
                    fig_income.update_layout(height=400)
                    st.plotly_chart(fig_income, use_container_width=True)

        # Expense breakdown
        if len(expense_df) > 0:
            st.subheader("Expense Breakdown")

            # Group by top-level account category
            expense_df["category"] = expense_df["account"].str.split(":").str[1]
            expense_summary = expense_df.groupby("category")["amount"].sum().reset_index()
            expense_summary["amount"] = expense_summary["amount"].abs()

            col1, col2 = st.columns(2)

            with col1:
                st.dataframe(
                    expense_summary.sort_values("amount", ascending=False),
                    column_config={
                        "category": "Expense Category",
                        "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    },
                    hide_index=True,
                )

            with col2:
                if len(expense_summary) > 0:
                    fig_expense = px.pie(
                        expense_summary,
                        values="amount",
                        names="category",
                        title="Expense Distribution",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig_expense.update_layout(height=400)
                    st.plotly_chart(fig_expense, use_container_width=True)

        # Monthly trends if viewing all months
        if selected_month == "All":
            st.subheader("Monthly Trends")

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

    except Exception as e:
        st.error(f"Error loading income statement data: {str(e)}")
        with st.expander("View detailed error information"):
            st.exception(e)


def show_balances(entries: List[data.Directive], options_map: Dict[str, Any]) -> None:
    """Display the account balances view with net worth analysis.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
    """
    st.header("⚖️ Account Balances")
    st.write("Current balances across all accounts")

    # Date selection for balance as of date
    as_of_date = st.date_input("Balance as of", value=datetime.now().date())

    try:
        # Get account balances
        balances_df = bc_utils.get_account_balances(entries, options_map, as_of_date)

        if len(balances_df) == 0:
            st.warning("No balance data found.")
            return

        # Filter out zero balances
        balances_df = balances_df[balances_df["amount"] != 0]

        # Categorize accounts
        all_accounts = balances_df["account"].unique()
        categorized_accounts = bc_utils.categorize_accounts(all_accounts)

        # Summary by category
        st.subheader("Balance Summary by Category")

        summary_data = []
        for category, accounts in categorized_accounts.items():
            if accounts:
                category_balance = balances_df[balances_df["account"].isin(accounts)][
                    "amount"
                ].sum()
                if abs(category_balance) > 0.01:  # Only show categories with meaningful balances
                    summary_data.append({"Category": category, "Balance": category_balance})

        if summary_data:
            summary_df = pd.DataFrame(summary_data)

            col1, col2 = st.columns(2)

            with col1:
                st.dataframe(
                    summary_df,
                    column_config={
                        "Category": "Account Category",
                        "Balance": st.column_config.NumberColumn("Balance", format="$%.2f"),
                    },
                    hide_index=True,
                )

            with col2:
                # Only show positive balances in pie chart (assets)
                positive_balances = summary_df[summary_df["Balance"] > 0]
                if len(positive_balances) > 0:
                    fig_summary = px.pie(
                        positive_balances,
                        values="Balance",
                        names="Category",
                        title="Asset Allocation",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                    )
                    fig_summary.update_layout(height=400)
                    st.plotly_chart(fig_summary, use_container_width=True)

        # Detailed balances by category
        for category, accounts in categorized_accounts.items():
            if accounts:
                category_df = balances_df[balances_df["account"].isin(accounts)]

                if len(category_df) > 0:
                    st.subheader(f"{category} Accounts")

                    # Sort by absolute amount descending
                    category_df = category_df.reindex(
                        category_df["amount"].abs().sort_values(ascending=False).index
                    )

                    # Create a nice display
                    display_df = category_df.copy()
                    display_df["amount_formatted"] = display_df["amount"].apply(
                        lambda x: f"${x:,.2f}"
                    )

                    st.dataframe(
                        display_df[["account", "currency", "amount"]],
                        column_config={
                            "account": "Account",
                            "currency": "Currency",
                            "amount": st.column_config.NumberColumn("Balance", format="$%.2f"),
                        },
                        hide_index=True,
                        use_container_width=True,
                    )

        # Net worth calculation
        st.subheader("Net Worth Summary")

        assets = balances_df[balances_df["account"].str.startswith("Assets:")]["amount"].sum()
        liabilities = balances_df[balances_df["account"].str.startswith("Liabilities:")][
            "amount"
        ].sum()
        net_worth = assets + liabilities  # Liabilities are negative in beancount

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Assets", f"${assets:,.2f}")

        with col2:
            st.metric("Total Liabilities", f"${abs(liabilities):,.2f}")

        with col3:
            st.metric("Net Worth", f"${net_worth:,.2f}")

        # Top accounts by balance
        st.subheader("Top Accounts by Balance")

        top_accounts = balances_df.nlargest(10, "amount")[["account", "amount"]]

        fig_top = px.bar(
            top_accounts,
            x="amount",
            y="account",
            orientation="h",
            title="Top 10 Accounts by Balance",
            labels={"amount": "Balance ($)", "account": "Account"},
        )
        fig_top.update_layout(height=500, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_top, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading balance data: {str(e)}")
        with st.expander("View detailed error information"):
            st.exception(e)


def show_journal(entries: List[data.Directive], options_map: Dict[str, Any]) -> None:
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

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Transactions", f"{total_transactions:,}")

        with col2:
            st.metric("Total Inflow", f"${total_inflow:,.2f}")

        with col3:
            st.metric("Total Outflow", f"${total_outflow:,.2f}")

        with col4:
            st.metric("Net Amount", f"${net_amount:,.2f}")

        # Transaction table
        st.subheader("Transactions")

        # Format the dataframe for display
        display_df = transactions_df.copy()
        display_df = display_df.sort_values("date", ascending=False)

        # Create a more compact account display
        display_df["account_short"] = display_df["account"].str.split(":").str[-1]

        # Format dates
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")

        st.dataframe(
            display_df[["date", "account_short", "description", "amount", "currency"]],
            column_config={
                "date": st.column_config.TextColumn("Date", width="small"),
                "account_short": st.column_config.TextColumn("Account", width="medium"),
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
                fig_daily = px.line(
                    daily_summary,
                    x="date",
                    y="amount",
                    title="Daily Transaction Flow",
                    labels={"date": "Date", "amount": "Net Amount ($)"},
                )
                fig_daily.update_layout(height=400)
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
        st.error(f"Error loading journal data: {str(e)}")
        with st.expander("View detailed error information"):
            st.exception(e)


def show_forecast(entries: List[data.Directive], options_map: Dict[str, Any]) -> None:
    """Display the financial forecast view with scenario modeling.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
    """
    st.header("🔮 Financial Forecast")
    st.write("Run what-if scenarios and simulations")

    # Get current balances for baseline
    try:
        current_balances = bc_utils.get_account_balances(entries, options_map)
        current_assets = current_balances[current_balances["account"].str.startswith("Assets:")][
            "amount"
        ].sum()
        current_liabilities = current_balances[
            current_balances["account"].str.startswith("Liabilities:")
        ]["amount"].sum()
        current_net_worth = current_assets + current_liabilities

        # Get recent income/expense trends
        income_trends = bc_utils.get_monthly_trends(entries, options_map, "Income:", 6)
        expense_trends = bc_utils.get_monthly_trends(entries, options_map, "Expenses:", 6)

        avg_monthly_income = income_trends["amount"].abs().mean() if len(income_trends) > 0 else 0
        avg_monthly_expenses = (
            expense_trends["amount"].abs().mean() if len(expense_trends) > 0 else 0
        )

        # Simulation parameters
        st.subheader("Current Financial Position")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Net Worth", f"${current_net_worth:,.2f}")
        with col2:
            st.metric("Avg Monthly Income", f"${avg_monthly_income:,.2f}")
        with col3:
            st.metric("Avg Monthly Expenses", f"${avg_monthly_expenses:,.2f}")

        st.markdown("---")

        # Scenario Selection
        st.subheader("Choose a Scenario")

        scenario = st.selectbox(
            "Simulation Type",
            [
                "Custom Scenario",
                "Home Purchase",
                "Investment Growth",
                "Emergency Fund",
                "Retirement Planning",
            ],
        )

        if scenario == "Custom Scenario":
            st.subheader("Custom Financial Scenario")

            col1, col2 = st.columns(2)
            with col1:
                monthly_income_change = st.number_input(
                    "Monthly Income Change ($)",
                    value=0.0,
                    help="Enter positive for income increase, negative for decrease",
                )
                monthly_expense_change = st.number_input(
                    "Monthly Expense Change ($)",
                    value=0.0,
                    help="Enter positive for expense increase, negative for decrease",
                )
                one_time_expense = st.number_input(
                    "One-time Major Expense ($)", value=0.0, help="Large purchase or expense"
                )

            with col2:
                annual_investment_return = st.slider(
                    "Expected Annual Investment Return (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=7.0,
                    step=0.5,
                )
                simulation_years = st.slider(
                    "Simulation Period (years)", min_value=1, max_value=30, value=5
                )

        elif scenario == "Home Purchase":
            st.subheader("Home Purchase Simulation")

            col1, col2 = st.columns(2)
            with col1:
                home_price = st.number_input("Home Price ($)", value=500000.0, step=10000.0)
                down_payment_pct = st.slider(
                    "Down Payment (%)", min_value=5.0, max_value=30.0, value=20.0, step=2.5
                )
                mortgage_rate = st.slider(
                    "Mortgage Rate (%)", min_value=3.0, max_value=8.0, value=6.5, step=0.25
                )

            with col2:
                mortgage_years = st.selectbox("Mortgage Term (years)", [15, 20, 25, 30], index=3)
                property_tax_annual = st.number_input(
                    "Annual Property Tax ($)", value=8000.0, step=500.0
                )
                insurance_annual = st.number_input(
                    "Annual Home Insurance ($)", value=1500.0, step=100.0
                )

            # Calculate mortgage details
            down_payment = home_price * (down_payment_pct / 100)
            loan_amount = home_price - down_payment
            monthly_rate = mortgage_rate / 100 / 12
            num_payments = mortgage_years * 12

            if loan_amount > 0 and monthly_rate > 0:
                monthly_payment = (
                    loan_amount
                    * (monthly_rate * (1 + monthly_rate) ** num_payments)
                    / ((1 + monthly_rate) ** num_payments - 1)
                )
            else:
                monthly_payment = 0

            monthly_other_costs = (property_tax_annual + insurance_annual) / 12
            total_monthly_housing = monthly_payment + monthly_other_costs

            # Set simulation parameters
            monthly_income_change = 0
            monthly_expense_change = total_monthly_housing
            one_time_expense = down_payment + 10000  # Down payment plus closing costs
            annual_investment_return = 7.0
            simulation_years = 5

            # Display home purchase summary
            st.info(
                f"""
            **Home Purchase Summary:**
            - Down Payment: ${down_payment:,.2f}
            - Loan Amount: ${loan_amount:,.2f}
            - Monthly Mortgage Payment: ${monthly_payment:,.2f}
            - Monthly Property Tax & Insurance: ${monthly_other_costs:,.2f}
            - **Total Monthly Housing Cost: ${total_monthly_housing:,.2f}**
            """
            )

        elif scenario == "Investment Growth":
            st.subheader("Investment Growth Simulation")

            col1, col2 = st.columns(2)
            with col1:
                monthly_investment = st.number_input(
                    "Monthly Investment ($)", value=1000.0, step=100.0
                )
                annual_investment_return = st.slider(
                    "Expected Annual Return (%)", min_value=0.0, max_value=15.0, value=8.0, step=0.5
                )

            with col2:
                simulation_years = st.slider(
                    "Investment Period (years)", min_value=1, max_value=40, value=10
                )

            monthly_income_change = 0
            monthly_expense_change = monthly_investment
            one_time_expense = 0

        elif scenario == "Emergency Fund":
            st.subheader("Emergency Fund Planning")

            col1, col2 = st.columns(2)
            with col1:
                target_months = st.slider(
                    "Target Months of Expenses", min_value=3, max_value=12, value=6
                )
                target_emergency_fund = avg_monthly_expenses * target_months

            with col2:
                monthly_savings = st.number_input(
                    "Monthly Emergency Fund Savings ($)", value=500.0, step=50.0
                )

            st.info(f"Target Emergency Fund: ${target_emergency_fund:,.2f}")

            monthly_income_change = 0
            monthly_expense_change = monthly_savings
            one_time_expense = 0
            annual_investment_return = 2.0  # Conservative savings account return
            simulation_years = int(target_emergency_fund / monthly_savings / 12) + 1

        elif scenario == "Retirement Planning":
            st.subheader("Retirement Planning Simulation")

            col1, col2 = st.columns(2)
            with col1:
                current_age = st.number_input("Current Age", value=35, min_value=20, max_value=70)
                retirement_age = st.number_input(
                    "Target Retirement Age", value=65, min_value=50, max_value=80
                )
                monthly_retirement_contribution = st.number_input(
                    "Monthly Retirement Contribution ($)", value=1000.0, step=100.0
                )

            with col2:
                annual_investment_return = st.slider(
                    "Expected Annual Return (%)", min_value=3.0, max_value=12.0, value=7.5, step=0.5
                )
                retirement_income_needed = st.number_input(
                    "Monthly Retirement Income Needed ($)", value=5000.0, step=500.0
                )

            simulation_years = retirement_age - current_age
            monthly_income_change = 0
            monthly_expense_change = monthly_retirement_contribution
            one_time_expense = 0

        # Run the simulation
        if st.button("Run Simulation", type="primary"):
            st.subheader("Simulation Results")

            # Calculate projections
            months = simulation_years * 12
            monthly_net_change = (avg_monthly_income + monthly_income_change) - (
                avg_monthly_expenses + monthly_expense_change
            )
            monthly_return_rate = annual_investment_return / 100 / 12

            projections = []
            running_balance = current_net_worth - one_time_expense

            for month in range(months + 1):
                if month == 0:
                    balance = running_balance
                else:
                    # Add monthly cash flow and investment growth
                    running_balance += monthly_net_change
                    running_balance *= 1 + monthly_return_rate

                    balance = running_balance

                projections.append(
                    {
                        "month": month,
                        "year": month / 12,
                        "balance": balance,
                        "date": datetime.now() + pd.DateOffset(months=month),
                    }
                )

            projection_df = pd.DataFrame(projections)

            # Display key metrics
            final_balance = projection_df.iloc[-1]["balance"]
            total_growth = final_balance - current_net_worth
            roi = (
                ((final_balance / current_net_worth) ** (1 / simulation_years) - 1) * 100
                if current_net_worth > 0
                else 0
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Final Net Worth", f"${final_balance:,.2f}")
            with col2:
                st.metric("Total Growth", f"${total_growth:,.2f}")
            with col3:
                st.metric("Annualized Return", f"{roi:.2f}%")

            # Plot projection
            fig_projection = px.line(
                projection_df,
                x="year",
                y="balance",
                title=f"Net Worth Projection - {scenario}",
                labels={"year": "Years from Now", "balance": "Net Worth ($)"},
            )

            # Add current net worth line
            fig_projection.add_hline(
                y=current_net_worth,
                line_dash="dash",
                line_color="red",
                annotation_text="Current Net Worth",
            )

            fig_projection.update_layout(height=500)
            st.plotly_chart(fig_projection, use_container_width=True)

            # Show yearly breakdown
            yearly_projections = projection_df[projection_df["month"] % 12 == 0].copy()
            yearly_projections["year_int"] = yearly_projections["month"] // 12

            st.subheader("Yearly Breakdown")
            yearly_display = yearly_projections[["year_int", "balance"]].copy()
            yearly_display.columns = ["Year", "Net Worth"]
            yearly_display["Year"] = yearly_display["Year"].astype(int)

            st.dataframe(
                yearly_display,
                column_config={
                    "Year": "Year",
                    "Net Worth": st.column_config.NumberColumn("Net Worth", format="$%.2f"),
                },
                hide_index=True,
                use_container_width=True,
            )

    except Exception as e:
        st.error(f"Error in forecast simulation: {str(e)}")
        with st.expander("View detailed error information"):
            st.exception(e)


def show_accounts() -> None:
    """Display the accounts information view with management tools."""
    st.header("🏦 Account Information")
    st.write("Detailed information about all your accounts")

    # Hardcoded account information - customize this section for your specific accounts
    account_info = {
        "Banking": {
            "Chase Checking": {
                "account_name": "Assets:US:Chase:Checking",
                "institution": "Chase Bank",
                "type": "Checking Account",
                "website": "https://chase.com",
                "login_method": "Online Banking / Mobile App",
                "notes": "Primary checking account for daily expenses",
                "important_info": "Debit card linked, direct deposit setup",
            },
            "Chase Savings": {
                "account_name": "Assets:US:Chase:Savings",
                "institution": "Chase Bank",
                "type": "Savings Account",
                "website": "https://chase.com",
                "login_method": "Online Banking / Mobile App",
                "notes": "Emergency fund and short-term savings",
                "important_info": "High yield savings, limited transfers",
            },
        },
        "Investment Accounts": {
            "Schwab Brokerage": {
                "account_name": "Assets:US:Schwab:Brokerage",
                "institution": "Charles Schwab",
                "type": "Taxable Brokerage",
                "website": "https://schwab.com",
                "login_method": "Online Portal / Mobile App",
                "notes": "Long-term investments, index funds",
                "important_info": "Tax-loss harvesting opportunities",
            },
            "401k": {
                "account_name": "Assets:US:Company:401k",
                "institution": "Company 401(k) Plan",
                "type": "Retirement Account (401k)",
                "website": "Company benefits portal",
                "login_method": "HR portal access",
                "notes": "Employer match up to 6%",
                "important_info": "Vested after 3 years, check contribution limits annually",
            },
            "Roth IRA": {
                "account_name": "Assets:US:Schwab:RothIRA",
                "institution": "Charles Schwab",
                "type": "Roth IRA",
                "website": "https://schwab.com",
                "login_method": "Online Portal / Mobile App",
                "notes": "Post-tax retirement savings",
                "important_info": "Contribution limit $6,500/year (2023), tax-free growth",
            },
        },
        "Credit Cards": {
            "Chase Sapphire": {
                "account_name": "Liabilities:US:Chase:CreditCard",
                "institution": "Chase Bank",
                "type": "Credit Card",
                "website": "https://chase.com",
                "login_method": "Online Banking / Mobile App",
                "notes": "Primary credit card, travel rewards",
                "important_info": "Auto-pay enabled, 2% cashback on travel",
            }
        },
        "Loans": {
            "Mortgage": {
                "account_name": "Liabilities:US:Mortgage",
                "institution": "Mortgage Company",
                "type": "Home Mortgage",
                "website": "Lender website",
                "login_method": "Lender portal",
                "notes": "30-year fixed rate mortgage",
                "important_info": "Principal residence, property taxes and insurance in escrow",
            }
        },
        "Other Assets": {
            "Home Value": {
                "account_name": "Assets:US:RealEstate:Home",
                "institution": "N/A",
                "type": "Real Estate",
                "website": "Zillow for estimates",
                "login_method": "N/A",
                "notes": "Primary residence valuation",
                "important_info": "Update value annually based on market conditions",
            }
        },
    }

    # Display account categories
    for category, accounts in account_info.items():
        st.subheader(f"📁 {category}")

        for account_name, details in accounts.items():
            with st.expander(f"🏦 {account_name}", expanded=False):

                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Account Details:**")
                    st.write(f"**Beancount Account:** `{details['account_name']}`")
                    st.write(f"**Institution:** {details['institution']}")
                    st.write(f"**Account Type:** {details['type']}")
                    st.write(f"**Website:** [{details['website']}]({details['website']})")
                    st.write(f"**Login Method:** {details['login_method']}")

                with col2:
                    st.write("**Notes & Important Info:**")
                    st.write(f"**Notes:** {details['notes']}")
                    st.write(f"**Important:** {details['important_info']}")

                    # Add quick actions
                    st.write("**Quick Actions:**")
                    if st.button(f"Copy Account Name", key=f"copy_{account_name}"):
                        st.code(details["account_name"])
                        st.success("Account name ready to copy!")

    st.markdown("---")

    # Account management section
    st.subheader("📋 Account Management")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Regular Account Reviews:**")
        st.write("- Monthly: Check all account balances")
        st.write("- Quarterly: Review investment allocations")
        st.write("- Annually: Update account information and beneficiaries")
        st.write("- As needed: Rebalance portfolios")

    with col2:
        st.write("**Security Reminders:**")
        st.write("- Enable 2FA on all financial accounts")
        st.write("- Use unique, strong passwords")
        st.write("- Monitor accounts regularly for fraud")
        st.write("- Keep contact info updated with institutions")

    # Account summary
    st.subheader("📊 Account Quick Reference")

    # Create a summary table
    summary_data = []
    for category, accounts in account_info.items():
        for account_name, details in accounts.items():
            summary_data.append(
                {
                    "Account Name": account_name,
                    "Category": category,
                    "Institution": details["institution"],
                    "Type": details["type"],
                    "Beancount Account": details["account_name"],
                }
            )

    summary_df = pd.DataFrame(summary_data)

    st.dataframe(
        summary_df,
        column_config={
            "Account Name": st.column_config.TextColumn("Account Name", width="medium"),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Institution": st.column_config.TextColumn("Institution", width="medium"),
            "Type": st.column_config.TextColumn("Type", width="medium"),
            "Beancount Account": st.column_config.TextColumn("Beancount Account", width="large"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # Contact information
    st.subheader("📞 Important Contacts")

    contacts = {
        "Chase Bank": "1-800-935-9935",
        "Charles Schwab": "1-866-855-9102",
        "Credit Bureau (Experian)": "1-888-397-3742",
        "Credit Bureau (Equifax)": "1-800-685-1111",
        "Credit Bureau (TransUnion)": "1-800-916-8800",
    }

    for institution, phone in contacts.items():
        st.write(f"**{institution}:** {phone}")

    # Tips and reminders
    st.subheader("💡 Financial Tips")

    st.info(
        """
    **Monthly Financial Checklist:**
    - [ ] Review all account balances and reconcile with beancount
    - [ ] Check credit card statements for accuracy
    - [ ] Verify automatic payments went through
    - [ ] Update any changed account information
    - [ ] Review investment performance and rebalance if needed
    - [ ] Check for any new fees or rate changes
    """
    )

    st.warning(
        """
    **Important Reminders:**
    - Keep beneficiary information updated on all accounts
    - Store account information securely (password manager recommended)
    - Review and update this account information quarterly
    - Notify spouse/partner of any account changes
    """
    )

    # Customization note
    st.markdown("---")
    st.info(
        "💻 **Customization Note:** Update the account information in the `show_accounts()` function in main.py to match your specific accounts and institutions."
    )


if __name__ == "__main__":
    main()
