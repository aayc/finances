"""Financial Forecast view for Finances."""

from typing import Dict, List, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

import beancount_utils as bc_utils
from views.common import show_summary_metrics, show_error_with_details
from views.advanced_forecast import (
    AdvancedForecastEngine, ScenarioParameters, IncomeProjection, ExpenseProjection,
    InvestmentProjection, LoanProjection, TaxRates, ScenarioType, create_comprehensive_charts
)


def show_forecast(entries: List, options_map: Dict[str, Any]) -> None:
    """Display the advanced financial forecast view with comprehensive scenario modeling.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
    """
    st.header("🔮 Advanced Financial Forecast")
    st.write("Comprehensive what-if scenario analysis with tax impact, risk modeling, and detailed projections")

    # Initialize the advanced forecast engine
    try:
        forecast_engine = AdvancedForecastEngine(entries, options_map)
    except Exception as e:
        show_error_with_details("Error initializing forecast engine", e)
        return

    # Display current financial state
    current_state = forecast_engine.current_balances

    st.subheader("📊 Current Financial Position")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Net Worth", f"${current_state['net_worth']:,.2f}")
    with col2:
        st.metric("Total Assets", f"${current_state['total_assets']:,.2f}")
    with col3:
        st.metric("Total Liabilities", f"${current_state['total_liabilities']:,.2f}")
    with col4:
        monthly_cash_flow = current_state['avg_monthly_income'] - current_state['avg_monthly_expenses']
        st.metric("Monthly Cash Flow", f"${monthly_cash_flow:,.2f}")

    # Show expense breakdown
    if current_state['expense_breakdown']:
        st.subheader("💸 Monthly Expense Analysis")

        expense_data = []
        for category, data in current_state['expense_breakdown'].items():
            expense_data.append({
                "Category": category,
                "Monthly Average": f"${data['monthly_average']:,.2f}",
                "Volatility (±)": f"${data['monthly_std']:,.2f}",
                "Annual Total": f"${data['total_last_year']:,.2f}",
                "Trend": "📈" if data['trend'] > 0 else "📉" if data['trend'] < 0 else "➡️"
            })

        expense_df = pd.DataFrame(expense_data)
        st.dataframe(expense_df, hide_index=True, use_container_width=True)

    st.markdown("---")


    # Advanced Scenario Configuration
    st.subheader("🎯 Scenario Configuration")

    # Scenario selection with more options
    scenario_options = [e.value for e in ScenarioType]
    scenario = st.selectbox(
        "Select Scenario Type",
        scenario_options,
        index=0
    )

    # Time horizon
    time_horizon = st.slider(
        "Forecast Time Horizon (years)",
        min_value=1,
        max_value=50,
        value=10,
        help="How many years to project into the future"
    )

    # Initialize scenario parameters
    params = ScenarioParameters(
        scenario_type=ScenarioType(scenario),
        time_horizon_years=time_horizon
    )

    # Comprehensive scenario configuration based on selection
    st.subheader("⚙️ Detailed Configuration")

    tab1, tab2, tab3, tab4 = st.tabs(["💰 Income", "💸 Expenses", "📈 Investments", "🏦 Taxes & Loans"])

    with tab1:
        st.write("**Income Projections**")
        col1, col2 = st.columns(2)

        with col1:
            base_salary = st.number_input(
                "Base Annual Salary ($)",
                value=float(current_state['avg_monthly_income'] * 12),
                step=5000.0,
                help="Current annual salary before bonuses"
            )

            salary_growth = st.slider(
                "Annual Salary Growth (%)",
                min_value=0.0,
                max_value=10.0,
                value=3.0,
                step=0.1,
                help="Expected annual salary increase"
            ) / 100

            bonus_amount = st.number_input(
                "Annual Bonus ($)",
                value=0.0,
                step=1000.0,
                help="Expected annual bonus amount"
            )

        with col2:
            other_income = st.number_input(
                "Other Annual Income ($)",
                value=0.0,
                step=1000.0,
                help="Investment income, side business, etc."
            )

            income_volatility = st.slider(
                "Income Volatility (%)",
                min_value=0.0,
                max_value=30.0,
                value=5.0,
                step=1.0,
                help="Standard deviation of income for risk modeling"
            ) / 100

            bonus_frequency = st.selectbox(
                "Bonus Frequency",
                [1, 2, 4],
                index=0,
                format_func=lambda x: {1: "Annual", 2: "Bi-annual", 4: "Quarterly"}[x]
            )

        params.income = IncomeProjection(
            base_salary=base_salary,
            salary_growth_rate=salary_growth,
            bonus_amount=bonus_amount,
            bonus_frequency=bonus_frequency,
            other_income=other_income,
            income_volatility=income_volatility
        )

    with tab2:
        st.write("**Expense Projections**")

        # Use historical expense data as baseline
        base_expenses = {}
        if current_state['expense_breakdown']:
            for category, data in current_state['expense_breakdown'].items():
                monthly_avg = data['monthly_average']
                base_expenses[category] = st.number_input(
                    f"{category} Monthly Budget ($)",
                    value=float(monthly_avg),
                    step=50.0,
                    key=f"expense_{category}"
                )
        else:
            # Default expense categories if no historical data
            default_categories = ["Housing", "Food", "Transportation", "Healthcare", "Entertainment", "Other"]
            for category in default_categories:
                base_expenses[category] = st.number_input(
                    f"{category} Monthly Budget ($)",
                    value=500.0,
                    step=50.0,
                    key=f"expense_{category}"
                )

        col1, col2 = st.columns(2)
        with col1:
            expense_growth = st.slider(
                "Annual Expense Growth (Inflation) (%)",
                min_value=0.0,
                max_value=10.0,
                value=2.5,
                step=0.1
            ) / 100

        with col2:
            # One-time major expenses
            st.write("**Major One-Time Expenses**")
            major_purchases = []

            num_purchases = st.number_input("Number of Major Purchases", min_value=0, max_value=10, value=0)
            for i in range(int(num_purchases)):
                col_a, col_b, col_c = st.columns([1, 1, 2])
                with col_a:
                    month = st.number_input(f"Month {i+1}", min_value=1, max_value=time_horizon*12, value=12, key=f"purchase_month_{i}")
                with col_b:
                    amount = st.number_input(f"Amount {i+1} ($)", value=10000.0, step=1000.0, key=f"purchase_amount_{i}")
                with col_c:
                    desc = st.text_input(f"Description {i+1}", value="Major Purchase", key=f"purchase_desc_{i}")

                major_purchases.append((int(month), float(amount), desc))

        params.expenses = ExpenseProjection(
            base_expenses=base_expenses,
            expense_growth_rate=expense_growth
        )
        params.major_purchases = major_purchases

    with tab3:
        st.write("**Investment & Market Assumptions**")
        col1, col2 = st.columns(2)

        with col1:
            expected_return = st.slider(
                "Expected Annual Investment Return (%)",
                min_value=0.0,
                max_value=15.0,
                value=7.0,
                step=0.1,
                help="Average annual return on invested assets"
            ) / 100

            volatility = st.slider(
                "Investment Volatility (%)",
                min_value=5.0,
                max_value=30.0,
                value=15.0,
                step=1.0,
                help="Standard deviation of annual returns for risk modeling"
            ) / 100

        with col2:
            monthly_investment = st.number_input(
                "Additional Monthly Investment ($)",
                value=0.0,
                step=100.0,
                help="Extra amount to invest monthly beyond current savings"
            )

            rebalancing_freq = st.selectbox(
                "Portfolio Rebalancing Frequency",
                [1, 3, 6, 12],
                index=3,
                format_func=lambda x: {1: "Monthly", 3: "Quarterly", 6: "Bi-annually", 12: "Annually"}[x]
            )

        params.investments = InvestmentProjection(
            expected_return=expected_return,
            volatility=volatility,
            rebalancing_frequency=rebalancing_freq,
            contribution_schedule={"additional": monthly_investment}
        )

    with tab4:
        st.write("**Tax Configuration**")
        col1, col2 = st.columns(2)

        with col1:
            filing_status = st.selectbox(
                "Tax Filing Status",
                ["Married Filing Jointly", "Single"],
                index=0
            )

            state_rate = st.slider(
                "State Income Tax Rate (%)",
                min_value=0.0,
                max_value=15.0,
                value=9.3,  # CA rate
                step=0.1
            ) / 100

            tax_advantaged_contrib = st.number_input(
                "Annual 401(k)/IRA Contribution ($)",
                value=0.0,
                step=1000.0,
                help="Reduces taxable income"
            )

        with col2:
            st.write("**Loan/Debt Information**")

            num_loans = st.number_input("Number of Loans/Debts", min_value=0, max_value=5, value=0)
            loans = []

            for i in range(int(num_loans)):
                st.write(f"**Loan {i+1}:**")
                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    principal = st.number_input(f"Principal {i+1} ($)", value=100000.0, step=1000.0, key=f"loan_principal_{i}")
                with col_b:
                    rate = st.number_input(f"Interest Rate {i+1} (%)", value=5.0, step=0.1, key=f"loan_rate_{i}") / 100
                with col_c:
                    term = st.number_input(f"Term {i+1} (months)", value=360, step=12, key=f"loan_term_{i}")

                loans.append(LoanProjection(
                    principal=principal,
                    interest_rate=rate,
                    term_months=int(term)
                ))

            params.loans = loans

        # Configure tax rates based on selection
        if filing_status == "Married Filing Jointly":
            tax_rates = TaxRates.get_2025_married_joint()
            tax_rates.state_rate = state_rate
        else:
            # Simplified single filer rates
            tax_rates = TaxRates(
                federal_brackets=[
                    (0.10, 11000),
                    (0.12, 44725),
                    (0.22, 95375),
                    (0.24, 182850),
                    (0.32, 231250),
                    (0.35, 578100),
                    (0.37, float('inf'))
                ],
                state_rate=state_rate
            )

        params.tax_rates = tax_rates
        params.tax_advantaged_accounts = {"401k": tax_advantaged_contrib}


    # Scenario-specific configurations
    if scenario == ScenarioType.HOME_PURCHASE.value:
        st.subheader("🏠 Home Purchase Details")
        col1, col2 = st.columns(2)

        with col1:
            home_price = st.number_input("Home Price ($)", value=800000.0, step=10000.0)
            down_payment_pct = st.slider("Down Payment (%)", min_value=5.0, max_value=30.0, value=20.0, step=2.5)
            mortgage_rate = st.slider("Mortgage Rate (%)", min_value=3.0, max_value=8.0, value=6.5, step=0.25) / 100

        with col2:
            mortgage_years = st.selectbox("Mortgage Term (years)", [15, 20, 25, 30], index=3)
            property_tax_annual = st.number_input("Annual Property Tax ($)", value=12000.0, step=500.0)
            insurance_annual = st.number_input("Annual Home Insurance ($)", value=2000.0, step=100.0)

        # Calculate mortgage details
        down_payment = home_price * (down_payment_pct / 100)
        loan_amount = home_price - down_payment

        # Add mortgage as a loan
        mortgage_loan = LoanProjection(
            principal=loan_amount,
            interest_rate=mortgage_rate,
            term_months=mortgage_years * 12
        )
        params.loans.append(mortgage_loan)

        # Add housing costs to expenses
        monthly_other_costs = (property_tax_annual + insurance_annual) / 12
        params.expenses.base_expenses["Housing"] = params.expenses.base_expenses.get("Housing", 0) + monthly_other_costs

        # Add down payment as major purchase
        params.major_purchases.append((1, down_payment + 15000, "Home Down Payment + Closing Costs"))

        # Calculate monthly payment for display
        if loan_amount > 0 and mortgage_rate > 0:
            monthly_rate = mortgage_rate / 12
            num_payments = mortgage_years * 12
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        else:
            monthly_payment = 0

        st.info(f"""
        **Home Purchase Summary:**
        - Down Payment: ${down_payment:,.2f}
        - Loan Amount: ${loan_amount:,.2f}
        - Monthly Mortgage Payment: ${monthly_payment:,.2f}
        - Monthly Property Tax & Insurance: ${monthly_other_costs:,.2f}
        - **Total Monthly Housing Cost: ${monthly_payment + monthly_other_costs:,.2f}**
        """)

    elif scenario == ScenarioType.INVESTMENT_GROWTH.value:
        st.subheader("📈 Investment Growth Focus")

        additional_investment = st.number_input(
            "Additional Monthly Investment ($)",
            value=2000.0,
            step=100.0,
            help="Extra monthly investment beyond current savings rate"
        )

        params.investments.contribution_schedule["additional"] += additional_investment

    elif scenario == ScenarioType.EMERGENCY_FUND.value:
        st.subheader("🚨 Emergency Fund Planning")

        col1, col2 = st.columns(2)
        with col1:
            target_months = st.slider("Target Months of Expenses", min_value=3, max_value=12, value=6)
            current_monthly_expenses = sum(params.expenses.base_expenses.values())
            target_emergency_fund = current_monthly_expenses * target_months

        with col2:
            monthly_savings = st.number_input("Monthly Emergency Savings ($)", value=800.0, step=50.0)

        st.info(f"Target Emergency Fund: ${target_emergency_fund:,.2f}")

        # Adjust investment return for conservative emergency fund
        params.investments.expected_return = 0.03  # Conservative savings rate
        params.investments.contribution_schedule["emergency"] = monthly_savings

    elif scenario == ScenarioType.RETIREMENT.value:
        st.subheader("🏖️ Retirement Planning")

        col1, col2 = st.columns(2)
        with col1:
            current_age = st.number_input("Current Age", value=35, min_value=20, max_value=70)
            retirement_age = st.number_input("Target Retirement Age", value=65, min_value=50, max_value=80)
            params.time_horizon_years = retirement_age - current_age

        with col2:
            monthly_retirement_contribution = st.number_input("Monthly Retirement Contribution ($)", value=2500.0, step=100.0)
            retirement_income_needed = st.number_input("Monthly Retirement Income Needed ($)", value=8000.0, step=500.0)

        # Increase 401k contribution
        params.tax_advantaged_accounts["401k"] = monthly_retirement_contribution * 12
        params.investments.contribution_schedule["retirement"] = monthly_retirement_contribution

        st.info(f"Years to retirement: {params.time_horizon_years}")
        st.info(f"Target retirement income: ${retirement_income_needed * 12:,.2f} annually")

    elif scenario == ScenarioType.CAREER_CHANGE.value:
        st.subheader("💼 Career Change Analysis")

        col1, col2 = st.columns(2)
        with col1:
            transition_month = st.number_input("Transition Month", min_value=1, max_value=time_horizon*12, value=12)
            new_salary = st.number_input("New Annual Salary ($)", value=params.income.base_salary * 0.8, step=5000.0)
            transition_costs = st.number_input("Career Transition Costs ($)", value=10000.0, step=1000.0)

        with col2:
            unpaid_months = st.number_input("Months Without Income", min_value=0, max_value=12, value=2)
            new_growth_rate = st.slider("New Career Growth Rate (%)", min_value=0.0, max_value=15.0, value=5.0) / 100

        # Model career transition
        params.major_purchases.append((int(transition_month), transition_costs, "Career Transition Costs"))

        # Adjust income for transition period
        if unpaid_months > 0:
            for month in range(int(transition_month), int(transition_month + unpaid_months)):
                # Would need more sophisticated income modeling for this
                pass

        # Update salary and growth after transition
        params.income.base_salary = new_salary
        params.income.salary_growth_rate = new_growth_rate

        st.info(f"""
        **Career Change Summary:**
        - Current Salary: ${params.income.base_salary:,.2f}
        - New Salary: ${new_salary:,.2f}
        - Transition Costs: ${transition_costs:,.2f}
        - Income Gap: {unpaid_months} months
        """)

    # Run Advanced Simulation
    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        run_forecast = st.button("🚀 Run Advanced Forecast", type="primary", use_container_width=True)
    with col2:
        include_monte_carlo = st.checkbox("Include Risk Analysis", value=True, help="Run Monte Carlo simulation for risk assessment")

    if run_forecast:
        try:
            with st.spinner("Running comprehensive financial forecast..."):
                # Run the advanced forecast
                result = forecast_engine.forecast_scenario(params)

                # Display key metrics
                st.subheader("📊 Forecast Summary")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "Final Net Worth",
                        f"${result.scenario_metrics['final_net_worth']:,.0f}",
                        delta=f"${result.scenario_metrics['total_growth']:,.0f}"
                    )
                with col2:
                    st.metric(
                        "Annualized Return",
                        f"{result.scenario_metrics['annualized_return']:.1f}%"
                    )
                with col3:
                    st.metric(
                        "Avg Monthly Cash Flow",
                        f"${result.scenario_metrics['avg_monthly_cash_flow']:,.0f}"
                    )
                with col4:
                    total_tax_burden = (result.scenario_metrics['total_taxes'] / result.scenario_metrics['total_income']) * 100
                    st.metric(
                        "Effective Tax Rate",
                        f"{total_tax_burden:.1f}%"
                    )

                # Risk Analysis
                if include_monte_carlo and result.risk_analysis:
                    st.subheader("🎲 Risk Analysis (Monte Carlo Simulation)")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Expected Outcome",
                            f"${result.risk_analysis['mean_outcome']:,.0f}",
                            help="Average outcome across 500 simulations"
                        )
                    with col2:
                        st.metric(
                            "5th Percentile",
                            f"${result.risk_analysis['percentile_5']:,.0f}",
                            help="Worst case scenario (5% chance of worse outcome)"
                        )
                    with col3:
                        probability_loss = result.risk_analysis['probability_of_loss'] * 100
                        st.metric(
                            "Probability of Loss",
                            f"{probability_loss:.1f}%",
                            help="Chance of ending worse than today"
                        )

                # Generate comprehensive charts
                charts = create_comprehensive_charts(result, params)

                st.subheader("📈 Detailed Analysis")

                # Display charts in tabs
                chart_tabs = st.tabs(["Net Worth Projection", "Cash Flow Analysis", "Tax Impact"])

                with chart_tabs[0]:
                    st.plotly_chart(charts[0], use_container_width=True)

                with chart_tabs[1]:
                    st.plotly_chart(charts[1], use_container_width=True)

                with chart_tabs[2]:
                    if len(charts) > 2:
                        st.plotly_chart(charts[2], use_container_width=True)

                # Detailed Tables
                st.subheader("📋 Detailed Projections")

                table_tabs = st.tabs(["Annual Summary", "Tax Summary", "Monthly Breakdown"])

                with table_tabs[0]:
                    display_annual = result.annual_summary[['year_int', 'net_worth', 'gross_income', 'expenses', 'taxes', 'net_cash_flow']].copy()
                    display_annual.columns = ['Year', 'Net Worth', 'Income', 'Expenses', 'Taxes', 'Net Cash Flow']

                    st.dataframe(
                        display_annual,
                        column_config={
                            "Year": st.column_config.NumberColumn("Year", format="%d"),
                            "Net Worth": st.column_config.NumberColumn("Net Worth", format="$%.0f"),
                            "Income": st.column_config.NumberColumn("Income", format="$%.0f"),
                            "Expenses": st.column_config.NumberColumn("Expenses", format="$%.0f"),
                            "Taxes": st.column_config.NumberColumn("Taxes", format="$%.0f"),
                            "Net Cash Flow": st.column_config.NumberColumn("Net Cash Flow", format="$%.0f"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                with table_tabs[1]:
                    st.dataframe(
                        result.tax_summary,
                        column_config={
                            "year": st.column_config.NumberColumn("Year", format="%d"),
                            "gross_income": st.column_config.NumberColumn("Gross Income", format="$%.0f"),
                            "taxes": st.column_config.NumberColumn("Total Taxes", format="$%.0f"),
                            "effective_tax_rate": st.column_config.NumberColumn("Effective Rate", format="%.1f%%"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                with table_tabs[2]:
                    # Show first 24 months of detailed breakdown
                    monthly_detail = result.monthly_projections.head(25)[['month', 'gross_income', 'expenses', 'taxes', 'net_cash_flow', 'investment_growth', 'net_worth']]
                    monthly_detail.columns = ['Month', 'Income', 'Expenses', 'Taxes', 'Net Flow', 'Inv Growth', 'Net Worth']

                    st.dataframe(
                        monthly_detail,
                        column_config={
                            "Month": st.column_config.NumberColumn("Month", format="%d"),
                            "Income": st.column_config.NumberColumn("Income", format="$%.0f"),
                            "Expenses": st.column_config.NumberColumn("Expenses", format="$%.0f"),
                            "Taxes": st.column_config.NumberColumn("Taxes", format="$%.0f"),
                            "Net Flow": st.column_config.NumberColumn("Net Flow", format="$%.0f"),
                            "Inv Growth": st.column_config.NumberColumn("Inv Growth", format="$%.0f"),
                            "Net Worth": st.column_config.NumberColumn("Net Worth", format="$%.0f"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )

                    st.caption("Showing first 24 months. Full projections available in annual summary.")

        except Exception as e:
            show_error_with_details("Error running advanced forecast", e)