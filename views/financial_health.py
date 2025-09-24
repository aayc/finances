"""Financial Health Dashboard for Finances."""

from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar

import beancount_utils as bc_utils
from views.common import (
    show_colored_summary_metrics,
    show_error_with_details,
    clean_account_name
)


def calculate_financial_ratios(
    entries: List,
    options_map: Dict[str, Any],
    current_date: Optional[datetime] = None
) -> Dict[str, float]:
    """Calculate key financial health ratios.

    Args:
        entries: Beancount entries
        options_map: Beancount options
        current_date: Date to calculate ratios for (defaults to now)

    Returns:
        Dictionary of financial ratios and metrics
    """
    if current_date is None:
        current_date = datetime.now()

    # Get current balances
    balances_df = bc_utils.get_account_balances(entries, options_map, current_date.date())

    # Get last 12 months of income and expenses for ratios
    income_12m, expenses_12m = bc_utils.get_monthly_income_statement(
        entries, options_map, current_date.year
    )

    # Calculate key amounts
    liquid_assets = balances_df[
        balances_df["account"].str.contains("Checking|Savings|Cash", case=False, na=False)
    ]["amount"].sum()

    total_assets = balances_df[
        balances_df["account"].str.startswith("Assets:")
    ]["amount"].sum()

    total_liabilities = abs(balances_df[
        balances_df["account"].str.startswith("Liabilities:")
    ]["amount"].sum())

    net_worth = total_assets - total_liabilities

    # Monthly income and expenses
    monthly_income = abs(income_12m["amount"].sum()) / 12 if len(income_12m) > 0 else 0
    monthly_expenses = abs(expenses_12m["amount"].sum()) / 12 if len(expenses_12m) > 0 else 0

    # Investment accounts (retirement, brokerage, etc.)
    investment_assets = balances_df[
        balances_df["account"].str.contains("401k|IRA|Brokerage|Investment", case=False, na=False)
    ]["amount"].sum()

    # Calculate ratios
    ratios = {
        "liquid_assets": liquid_assets,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "investment_assets": investment_assets,

        # Key ratios
        "emergency_fund_months": liquid_assets / monthly_expenses if monthly_expenses > 0 else 0,
        "savings_rate": (monthly_income - monthly_expenses) / monthly_income if monthly_income > 0 else 0,
        "debt_to_income": (total_liabilities * 12) / (monthly_income * 12) if monthly_income > 0 else 0,
        "debt_to_assets": total_liabilities / total_assets if total_assets > 0 else 0,
        "investment_ratio": investment_assets / total_assets if total_assets > 0 else 0,
        "liquidity_ratio": liquid_assets / monthly_expenses if monthly_expenses > 0 else 0,
    }

    return ratios


def get_health_score(ratios: Dict[str, float]) -> Tuple[int, str, str]:
    """Calculate overall financial health score.

    Args:
        ratios: Dictionary of financial ratios

    Returns:
        Tuple of (score, grade, explanation)
    """
    score = 0
    explanations = []

    # Emergency fund (25 points max)
    emergency_months = ratios["emergency_fund_months"]
    if emergency_months >= 6:
        score += 25
        explanations.append("✅ Excellent emergency fund (6+ months)")
    elif emergency_months >= 3:
        score += 20
        explanations.append("👍 Good emergency fund (3-6 months)")
    elif emergency_months >= 1:
        score += 10
        explanations.append("⚠️ Minimal emergency fund (1-3 months)")
    else:
        explanations.append("❌ No emergency fund")

    # Savings rate (25 points max)
    savings_rate = ratios["savings_rate"]
    if savings_rate >= 0.20:
        score += 25
        explanations.append("✅ Excellent savings rate (20%+)")
    elif savings_rate >= 0.10:
        score += 20
        explanations.append("👍 Good savings rate (10-20%)")
    elif savings_rate >= 0.05:
        score += 10
        explanations.append("⚠️ Moderate savings rate (5-10%)")
    else:
        explanations.append("❌ Low or negative savings rate")

    # Debt management (25 points max)
    debt_to_income = ratios["debt_to_income"]
    if debt_to_income <= 0.1:
        score += 25
        explanations.append("✅ Excellent debt management (<10% DTI)")
    elif debt_to_income <= 0.2:
        score += 20
        explanations.append("👍 Good debt management (10-20% DTI)")
    elif debt_to_income <= 0.4:
        score += 10
        explanations.append("⚠️ Moderate debt levels (20-40% DTI)")
    else:
        explanations.append("❌ High debt levels (40%+ DTI)")

    # Investment diversification (25 points max)
    investment_ratio = ratios["investment_ratio"]
    if investment_ratio >= 0.3:
        score += 25
        explanations.append("✅ Well diversified investments (30%+ of assets)")
    elif investment_ratio >= 0.15:
        score += 20
        explanations.append("👍 Good investment allocation (15-30%)")
    elif investment_ratio >= 0.05:
        score += 10
        explanations.append("⚠️ Some investments (5-15%)")
    else:
        explanations.append("❌ Limited investment diversification")

    # Determine grade
    if score >= 90:
        grade = "A+"
        color = "green"
    elif score >= 80:
        grade = "A"
        color = "green"
    elif score >= 70:
        grade = "B"
        color = "green"
    elif score >= 60:
        grade = "C"
        color = "orange"
    elif score >= 50:
        grade = "D"
        color = "red"
    else:
        grade = "F"
        color = "red"

    return score, grade, explanations, color


def show_progress_gauge(value: float, title: str, target: float, format_func=None) -> None:
    """Show a progress gauge for a metric.

    Args:
        value: Current value
        title: Gauge title
        target: Target value for 100%
        format_func: Function to format the value display
    """
    if format_func is None:
        format_func = lambda x: f"{x:.1f}"

    # Calculate progress percentage
    progress = min(value / target * 100, 100) if target > 0 else 0

    # Determine color based on progress
    if progress >= 100:
        color = "#28a745"  # Green
    elif progress >= 75:
        color = "#ffc107"  # Yellow
    elif progress >= 50:
        color = "#fd7e14"  # Orange
    else:
        color = "#dc3545"  # Red

    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = progress,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        delta = {'reference': 100},
        gauge = {
            'axis': {'range': [None, 120]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 75], 'color': "gray"},
                {'range': [75, 100], 'color': "lightgreen"},
                {'range': [100, 120], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 100
            }
        }
    ))

    fig.update_layout(
        height=300,
        font = {'color': "darkblue", 'family': "Arial"}
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show actual values below gauge
    st.markdown(f"**Current:** {format_func(value)}")
    st.markdown(f"**Target:** {format_func(target)}")


def show_spending_trend_analysis(entries: List, options_map: Dict[str, Any]) -> None:
    """Show spending trend analysis over the last 6 months."""
    st.subheader("📊 6-Month Spending Trends")

    current_date = datetime.now()
    monthly_data = []

    for i in range(6):
        month_date = current_date - timedelta(days=30 * i)
        year = month_date.year
        month = month_date.month

        _, expenses_df = bc_utils.get_monthly_income_statement(
            entries, options_map, year, month
        )

        total_expenses = abs(expenses_df["amount"].sum()) if len(expenses_df) > 0 else 0
        month_name = calendar.month_abbr[month]

        monthly_data.append({
            "month": f"{month_name} {year}",
            "expenses": total_expenses,
            "date": month_date.replace(day=1)
        })

    # Sort by date
    monthly_data = sorted(monthly_data, key=lambda x: x["date"])

    if monthly_data:
        df = pd.DataFrame(monthly_data)

        # Calculate trend
        if len(df) >= 2:
            trend = (df["expenses"].iloc[-1] - df["expenses"].iloc[0]) / df["expenses"].iloc[0] * 100
            trend_text = f"{'↗️ +' if trend > 0 else '↘️ '}{trend:.1f}% vs 6 months ago"
            trend_color = "red" if trend > 10 else "green" if trend < -5 else "orange"
        else:
            trend_text = "Insufficient data"
            trend_color = "gray"

        col1, col2 = st.columns([3, 1])

        with col1:
            fig = px.line(df, x="month", y="expenses",
                         title="Monthly Spending Trend",
                         markers=True)
            fig.update_layout(
                height=300,
                yaxis=dict(tickformat="$,.0f")
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.metric("Trend", trend_text, delta=None)
            st.markdown(f"<div style='color: {trend_color}; font-weight: bold;'>{trend_text}</div>",
                       unsafe_allow_html=True)


def show_financial_health(entries: List, options_map: Dict[str, Any]) -> None:
    """Display the financial health dashboard.

    Args:
        entries: List of beancount entries
        options_map: Beancount options configuration
    """
    st.header("🏥 Financial Health Dashboard")
    st.write("Comprehensive analysis of your financial well-being")

    try:
        # Calculate financial ratios
        with st.spinner("Analyzing your financial health..."):
            ratios = calculate_financial_ratios(entries, options_map)
            score, grade, explanations, grade_color = get_health_score(ratios)

        # Overall health score
        st.subheader("🎯 Overall Financial Health")

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            st.markdown(f"""
            <div style='text-align: center; padding: 20px; border-radius: 10px; background-color: #f0f2f6;'>
                <h1 style='color: {grade_color}; margin: 0; font-size: 4rem;'>{grade}</h1>
                <h3 style='margin: 0;'>Grade</h3>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style='text-align: center; padding: 20px; border-radius: 10px; background-color: #f0f2f6;'>
                <h1 style='color: {grade_color}; margin: 0; font-size: 4rem;'>{score}</h1>
                <h3 style='margin: 0;'>Score</h3>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.write("**Key Areas:**")
            for explanation in explanations:
                st.write(f"• {explanation}")

        # Key financial metrics
        st.subheader("💰 Key Financial Metrics")

        show_colored_summary_metrics([
            {
                "label": "Net Worth",
                "value": f"${ratios['net_worth']:,.0f}",
                "color": "green" if ratios['net_worth'] > 0 else "red"
            },
            {
                "label": "Monthly Income",
                "value": f"${ratios['monthly_income']:,.0f}"
            },
            {
                "label": "Monthly Expenses",
                "value": f"${ratios['monthly_expenses']:,.0f}"
            },
            {
                "label": "Savings Rate",
                "value": f"{ratios['savings_rate']:.1%}",
                "color": "green" if ratios['savings_rate'] >= 0.1 else "red" if ratios['savings_rate'] < 0 else "orange"
            }
        ])

        # Progress gauges for key ratios
        st.subheader("📈 Financial Health Indicators")

        gauge_col1, gauge_col2, gauge_col3 = st.columns(3)

        with gauge_col1:
            show_progress_gauge(
                ratios["emergency_fund_months"],
                "Emergency Fund",
                6.0,  # Target: 6 months
                lambda x: f"{x:.1f} months"
            )

        with gauge_col2:
            show_progress_gauge(
                ratios["savings_rate"] * 100,
                "Savings Rate",
                20.0,  # Target: 20%
                lambda x: f"{x:.1f}%"
            )

        with gauge_col3:
            show_progress_gauge(
                max(0, 100 - ratios["debt_to_income"] * 100),
                "Debt Management",
                100.0,  # Target: Low debt
                lambda x: f"{100-x:.1f}% DTI"
            )

        # Asset allocation breakdown
        st.subheader("🥧 Asset Allocation")

        allocation_data = []
        if ratios["liquid_assets"] > 0:
            allocation_data.append({"category": "Cash & Equivalents", "amount": ratios["liquid_assets"]})
        if ratios["investment_assets"] > 0:
            allocation_data.append({"category": "Investments", "amount": ratios["investment_assets"]})

        other_assets = ratios["total_assets"] - ratios["liquid_assets"] - ratios["investment_assets"]
        if other_assets > 0:
            allocation_data.append({"category": "Other Assets", "amount": other_assets})

        if allocation_data:
            allocation_df = pd.DataFrame(allocation_data)

            col1, col2 = st.columns(2)

            with col1:
                fig = px.pie(allocation_df, values="amount", names="category",
                           title="Asset Distribution")
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Asset allocation table
                allocation_df["percentage"] = allocation_df["amount"] / allocation_df["amount"].sum() * 100
                allocation_df["amount_formatted"] = allocation_df["amount"].apply(lambda x: f"${x:,.0f}")
                allocation_df["percentage_formatted"] = allocation_df["percentage"].apply(lambda x: f"{x:.1f}%")

                st.dataframe(
                    allocation_df[["category", "amount_formatted", "percentage_formatted"]],
                    column_config={
                        "category": "Asset Category",
                        "amount_formatted": "Amount",
                        "percentage_formatted": "Percentage"
                    },
                    hide_index=True,
                    use_container_width=True
                )

        # Monthly trends
        show_spending_trend_analysis(entries, options_map)

        # Recommendations
        st.subheader("💡 Personalized Recommendations")

        recommendations = []

        if ratios["emergency_fund_months"] < 3:
            recommendations.append("🚨 **Priority:** Build emergency fund to 3-6 months of expenses")

        if ratios["savings_rate"] < 0.1:
            recommendations.append("📈 **Focus:** Increase savings rate to at least 10%")

        if ratios["debt_to_income"] > 0.3:
            recommendations.append("💳 **Action:** Work on reducing debt burden")

        if ratios["investment_ratio"] < 0.15:
            recommendations.append("📊 **Opportunity:** Consider increasing investment allocation")

        if not recommendations:
            recommendations.append("🎉 **Great job!** Your financial health looks strong. Keep up the good work!")

        for rec in recommendations:
            st.write(rec)

    except Exception as e:
        show_error_with_details("Error calculating financial health", e)