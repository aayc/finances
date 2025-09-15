"""Financial Forecast view for OurFinance."""

from typing import Dict, List, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import beancount_utils as bc_utils
from views.common import show_summary_metrics, show_error_with_details


def show_forecast(entries: List, options_map: Dict[str, Any]) -> None:
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

        # Calculate average monthly income, filtering out extreme outliers
        if len(income_trends) > 0:
            income_amounts = income_trends["amount"].abs()
            # Filter out outliers that are more than 3x the median (likely one-time bonuses, stock sales, etc.)
            median_income = income_amounts.median()
            if median_income > 0:
                filtered_income = income_amounts[income_amounts <= median_income * 3]
                avg_monthly_income = filtered_income.mean() if len(filtered_income) > 0 else median_income
            else:
                avg_monthly_income = median_income
        else:
            avg_monthly_income = 0
        avg_monthly_expenses = (
            expense_trends["amount"].abs().mean() if len(expense_trends) > 0 else 0
        )

        # Current Financial Position
        st.subheader("Current Financial Position")

        show_summary_metrics([
            {
                "label": "Current Net Worth",
                "value": f"${current_net_worth:,.2f}"
            },
            {
                "label": "Avg Monthly Income",
                "value": f"${avg_monthly_income:,.2f}"
            },
            {
                "label": "Avg Monthly Expenses",
                "value": f"${avg_monthly_expenses:,.2f}"
            }
        ])

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

        # Initialize variables
        monthly_income_change = 0.0
        monthly_expense_change = 0.0
        one_time_expense = 0.0
        annual_investment_return = 7.0
        simulation_years = 5

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

            show_summary_metrics([
                {
                    "label": "Final Net Worth",
                    "value": f"${final_balance:,.2f}"
                },
                {
                    "label": "Total Growth",
                    "value": f"${total_growth:,.2f}"
                },
                {
                    "label": "Annualized Return",
                    "value": f"{roi:.2f}%"
                }
            ])

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
        show_error_with_details("Error in forecast simulation", e)