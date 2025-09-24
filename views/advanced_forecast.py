"""Advanced Financial Forecast Engine for Finances."""

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import beancount_utils as bc_utils


class ScenarioType(Enum):
    CUSTOM = "Custom Scenario"
    HOME_PURCHASE = "Home Purchase"
    INVESTMENT_GROWTH = "Investment Growth"
    EMERGENCY_FUND = "Emergency Fund"
    RETIREMENT = "Retirement Planning"
    CAREER_CHANGE = "Career Change"
    EDUCATION = "Education Investment"
    BUSINESS_START = "Business Startup"
    DEBT_PAYOFF = "Debt Payoff"


class TaxBracket(Enum):
    SINGLE_2025 = "single_2025"
    MARRIED_JOINT_2025 = "married_joint_2025"


@dataclass
class TaxRates:
    """Tax rate configurations for different brackets and years."""
    federal_brackets: List[Tuple[float, float]] = field(default_factory=list)
    state_rate: float = 0.0
    fica_rate: float = 0.0765  # Social Security + Medicare
    ltcg_rate: float = 0.15  # Long-term capital gains
    stcg_rate: float = 0.0  # Short-term capital gains (taxed as ordinary income)

    @classmethod
    def get_2025_married_joint(cls) -> 'TaxRates':
        return cls(
            federal_brackets=[
                (0.10, 23200),
                (0.12, 94300),
                (0.22, 201050),
                (0.24, 383900),
                (0.32, 487450),
                (0.35, 731200),
                (0.37, float('inf'))
            ],
            state_rate=0.093,  # CA top rate
            fica_rate=0.0765,
            ltcg_rate=0.15,
        )


@dataclass
class IncomeProjection:
    """Income projection parameters."""
    base_salary: float = 0.0
    salary_growth_rate: float = 0.03  # 3% annually
    bonus_amount: float = 0.0
    bonus_frequency: int = 1  # times per year
    investment_income: float = 0.0
    other_income: float = 0.0
    income_volatility: float = 0.0  # Standard deviation as % of income


@dataclass
class ExpenseProjection:
    """Expense projection parameters."""
    base_expenses: Dict[str, float] = field(default_factory=dict)
    expense_growth_rate: float = 0.025  # 2.5% inflation
    variable_expenses: Dict[str, float] = field(default_factory=dict)  # One-time or irregular
    seasonal_adjustments: Dict[str, Dict[int, float]] = field(default_factory=dict)  # month -> multiplier


@dataclass
class InvestmentProjection:
    """Investment and market projection parameters."""
    expected_return: float = 0.07  # 7% annually
    volatility: float = 0.15  # 15% standard deviation
    rebalancing_frequency: int = 12  # months
    asset_allocation: Dict[str, float] = field(default_factory=dict)
    contribution_schedule: Dict[str, float] = field(default_factory=dict)  # account -> monthly amount


@dataclass
class LoanProjection:
    """Loan and debt projection parameters."""
    principal: float = 0.0
    interest_rate: float = 0.0
    term_months: int = 0
    extra_payments: float = 0.0  # monthly extra payment


@dataclass
class ScenarioParameters:
    """Complete scenario configuration."""
    scenario_type: ScenarioType
    time_horizon_years: int = 10

    # Core projections
    income: IncomeProjection = field(default_factory=IncomeProjection)
    expenses: ExpenseProjection = field(default_factory=ExpenseProjection)
    investments: InvestmentProjection = field(default_factory=InvestmentProjection)
    loans: List[LoanProjection] = field(default_factory=list)

    # Tax configuration
    tax_rates: TaxRates = field(default_factory=TaxRates.get_2025_married_joint)
    tax_advantaged_accounts: Dict[str, float] = field(default_factory=dict)  # account -> contribution limit

    # One-time events
    major_purchases: List[Tuple[int, float, str]] = field(default_factory=list)  # (month, amount, description)
    windfalls: List[Tuple[int, float, str]] = field(default_factory=list)  # (month, amount, description)


@dataclass
class ForecastResult:
    """Forecast calculation results."""
    monthly_projections: pd.DataFrame
    annual_summary: pd.DataFrame
    tax_summary: pd.DataFrame
    scenario_metrics: Dict[str, Any]
    risk_analysis: Dict[str, Any]


class AdvancedForecastEngine:
    """Sophisticated financial forecasting engine."""

    def __init__(self, entries: List, options_map: Dict[str, Any]):
        self.entries = entries
        self.options_map = options_map
        self.current_balances = self._get_current_state()

    def _get_current_state(self) -> Dict[str, Any]:
        """Extract current financial state from beancount data."""
        balances = bc_utils.get_account_balances(self.entries, self.options_map)

        # Categorize current balances
        assets = balances[balances["account"].str.startswith("Assets:")]["amount"].sum()
        liabilities = balances[balances["account"].str.startswith("Liabilities:")]["amount"].sum()
        net_worth = assets + liabilities  # liabilities are negative

        # Get historical income/expense patterns
        income_trends = bc_utils.get_monthly_trends(self.entries, self.options_map, "Income:", 12)
        expense_trends = bc_utils.get_monthly_trends(self.entries, self.options_map, "Expenses:", 12)

        # Calculate average monthly cash flow
        avg_income = abs(income_trends["amount"].mean()) if len(income_trends) > 0 else 0
        avg_expenses = expense_trends["amount"].mean() if len(expense_trends) > 0 else 0

        # Get detailed expense breakdown by category
        expense_breakdown = self._analyze_expense_patterns()

        return {
            "net_worth": net_worth,
            "total_assets": assets,
            "total_liabilities": abs(liabilities),
            "avg_monthly_income": avg_income,
            "avg_monthly_expenses": avg_expenses,
            "expense_breakdown": expense_breakdown,
            "account_balances": balances
        }

    def _analyze_expense_patterns(self) -> Dict[str, Any]:
        """Analyze historical expense patterns for forecasting."""
        expense_analysis = {}

        # Get last 12 months of expenses by category
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)

        transactions = bc_utils.get_transactions(
            self.entries, self.options_map,
            start_date=start_date, end_date=end_date
        )

        if len(transactions) == 0:
            return {}

        # Filter expense transactions
        expense_txns = transactions[
            transactions["account"].str.startswith("Expenses:")
        ].copy()

        if len(expense_txns) == 0:
            return {}

        # Group by top-level expense category
        expense_txns["category"] = expense_txns["account"].str.extract(r"Expenses:([^:]+)")[0]

        # Calculate monthly averages and volatility by category
        expense_txns["year_month"] = expense_txns["date"].dt.to_period("M")
        monthly_by_category = expense_txns.groupby(["category", "year_month"])["amount"].sum().reset_index()

        for category in monthly_by_category["category"].unique():
            cat_data = monthly_by_category[monthly_by_category["category"] == category]
            expense_analysis[category] = {
                "monthly_average": cat_data["amount"].mean(),
                "monthly_std": cat_data["amount"].std(),
                "total_last_year": cat_data["amount"].sum(),
                "trend": self._calculate_trend(cat_data["amount"].values)
            }

        return expense_analysis

    def _calculate_trend(self, values: np.ndarray) -> float:
        """Calculate simple linear trend slope."""
        if len(values) < 2:
            return 0.0
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        return slope

    def calculate_taxes(self, gross_income: float, investment_gains: float,
                       tax_rates: TaxRates, tax_advantaged_contrib: float = 0) -> Dict[str, float]:
        """Calculate comprehensive tax liability."""
        # Adjust gross income for tax-advantaged contributions
        taxable_income = max(0, gross_income - tax_advantaged_contrib)

        # Federal income tax
        federal_tax = self._calculate_progressive_tax(taxable_income, tax_rates.federal_brackets)

        # State tax (flat rate for simplicity)
        state_tax = taxable_income * tax_rates.state_rate

        # FICA taxes (on gross income, not reduced by 401k)
        fica_tax = gross_income * tax_rates.fica_rate

        # Investment gains tax
        ltcg_tax = investment_gains * tax_rates.ltcg_rate

        total_tax = federal_tax + state_tax + fica_tax + ltcg_tax

        return {
            "federal_tax": federal_tax,
            "state_tax": state_tax,
            "fica_tax": fica_tax,
            "investment_tax": ltcg_tax,
            "total_tax": total_tax,
            "effective_rate": total_tax / max(gross_income, 1),
            "marginal_rate": self._get_marginal_rate(taxable_income, tax_rates.federal_brackets) + tax_rates.state_rate
        }

    def _calculate_progressive_tax(self, income: float, brackets: List[Tuple[float, float]]) -> float:
        """Calculate tax using progressive brackets."""
        if income <= 0:
            return 0

        tax = 0
        prev_threshold = 0

        for rate, threshold in brackets:
            if income <= prev_threshold:
                break

            taxable_in_bracket = min(income, threshold) - prev_threshold
            tax += taxable_in_bracket * rate
            prev_threshold = threshold

            if income <= threshold:
                break

        return tax

    def _get_marginal_rate(self, income: float, brackets: List[Tuple[float, float]]) -> float:
        """Get marginal tax rate for given income level."""
        for rate, threshold in brackets:
            if income <= threshold:
                return rate
        return brackets[-1][0]  # Top bracket rate

    def run_monte_carlo_simulation(self, params: ScenarioParameters,
                                 num_simulations: int = 1000) -> Dict[str, Any]:
        """Run Monte Carlo simulation for risk analysis."""
        results = []

        for _ in range(num_simulations):
            # Generate random returns and income variations
            annual_returns = np.random.normal(
                params.investments.expected_return,
                params.investments.volatility,
                params.time_horizon_years
            )

            income_variations = np.random.normal(
                1.0, params.income.income_volatility,
                params.time_horizon_years
            )

            # Run single simulation
            sim_result = self._run_single_simulation(params, annual_returns, income_variations)
            results.append(sim_result["final_net_worth"])

        results = np.array(results)

        return {
            "mean_outcome": np.mean(results),
            "median_outcome": np.median(results),
            "std_outcome": np.std(results),
            "percentile_5": np.percentile(results, 5),
            "percentile_25": np.percentile(results, 25),
            "percentile_75": np.percentile(results, 75),
            "percentile_95": np.percentile(results, 95),
            "probability_of_loss": np.mean(results < self.current_balances["net_worth"]),
            "value_at_risk_5": self.current_balances["net_worth"] - np.percentile(results, 5)
        }

    def _run_single_simulation(self, params: ScenarioParameters,
                             annual_returns: np.ndarray,
                             income_variations: np.ndarray) -> Dict[str, Any]:
        """Run a single simulation with given random variables."""
        net_worth = self.current_balances["net_worth"]

        for year in range(params.time_horizon_years):
            # Calculate annual income with variation
            base_income = params.income.base_salary * (1 + params.income.salary_growth_rate) ** year
            varied_income = base_income * income_variations[year]
            total_income = varied_income + params.income.bonus_amount + params.income.other_income

            # Calculate annual expenses with inflation
            total_expenses = sum(params.expenses.base_expenses.values()) * (1 + params.expenses.expense_growth_rate) ** year

            # Calculate taxes
            tax_info = self.calculate_taxes(total_income, 0, params.tax_rates)

            # Net cash flow
            annual_cash_flow = total_income - total_expenses - tax_info["total_tax"]

            # Investment growth
            investment_growth = net_worth * annual_returns[year]

            # Update net worth
            net_worth += annual_cash_flow + investment_growth

        return {"final_net_worth": net_worth}

    def forecast_scenario(self, params: ScenarioParameters) -> ForecastResult:
        """Run comprehensive scenario forecast."""
        months = params.time_horizon_years * 12
        projections = []

        current_net_worth = self.current_balances["net_worth"]
        current_income = params.income.base_salary / 12
        current_expenses = sum(params.expenses.base_expenses.values())

        # Monthly projections
        for month in range(months + 1):
            year = month // 12
            month_of_year = (month % 12) + 1

            # Income calculation with growth
            monthly_income = (params.income.base_salary / 12) * (1 + params.income.salary_growth_rate) ** (month / 12)
            monthly_income += params.income.other_income / 12

            # Add bonus if applicable
            if month > 0 and month % (12 // params.income.bonus_frequency) == 0:
                monthly_income += params.income.bonus_amount / params.income.bonus_frequency

            # Expense calculation with inflation
            monthly_expenses = 0
            for category, base_amount in params.expenses.base_expenses.items():
                inflated_amount = base_amount * (1 + params.expenses.expense_growth_rate) ** (month / 12)

                # Apply seasonal adjustments if configured
                if category in params.expenses.seasonal_adjustments:
                    seasonal_mult = params.expenses.seasonal_adjustments[category].get(month_of_year, 1.0)
                    inflated_amount *= seasonal_mult

                monthly_expenses += inflated_amount

            # Calculate monthly taxes (simplified)
            annual_income = monthly_income * 12
            monthly_tax_info = self.calculate_taxes(annual_income, 0, params.tax_rates)
            monthly_taxes = monthly_tax_info["total_tax"] / 12

            # Investment growth
            monthly_return = (1 + params.investments.expected_return) ** (1/12) - 1
            investment_growth = current_net_worth * monthly_return

            # Handle major purchases and windfalls
            one_time_events = 0
            for event_month, amount, desc in params.major_purchases:
                if event_month == month:
                    one_time_events -= amount

            for event_month, amount, desc in params.windfalls:
                if event_month == month:
                    one_time_events += amount

            # Net cash flow
            net_cash_flow = monthly_income - monthly_expenses - monthly_taxes + one_time_events

            # Update net worth
            if month > 0:
                current_net_worth += net_cash_flow + investment_growth

            projections.append({
                "month": month,
                "year": month / 12,
                "date": datetime.now() + pd.DateOffset(months=month),
                "gross_income": monthly_income,
                "expenses": monthly_expenses,
                "taxes": monthly_taxes,
                "net_cash_flow": net_cash_flow,
                "investment_growth": investment_growth,
                "net_worth": current_net_worth,
                "one_time_events": one_time_events
            })

        projections_df = pd.DataFrame(projections)

        # Generate annual summary
        annual_summary = projections_df[projections_df["month"] % 12 == 0].copy()
        annual_summary["year_int"] = (annual_summary["month"] // 12).astype(int)

        # Tax summary
        tax_summary = self._generate_tax_summary(projections_df, params)

        # Scenario metrics
        final_net_worth = projections_df.iloc[-1]["net_worth"]
        total_growth = final_net_worth - self.current_balances["net_worth"]
        annualized_return = ((final_net_worth / self.current_balances["net_worth"]) ** (1 / params.time_horizon_years) - 1) * 100 if self.current_balances["net_worth"] > 0 else 0

        metrics = {
            "final_net_worth": final_net_worth,
            "total_growth": total_growth,
            "annualized_return": annualized_return,
            "total_income": projections_df["gross_income"].sum(),
            "total_expenses": projections_df["expenses"].sum(),
            "total_taxes": projections_df["taxes"].sum(),
            "total_investment_growth": projections_df["investment_growth"].sum(),
            "avg_monthly_cash_flow": projections_df["net_cash_flow"].mean(),
            "years_to_break_even": self._calculate_break_even_years(projections_df) if total_growth < 0 else None
        }

        # Risk analysis via Monte Carlo
        risk_analysis = self.run_monte_carlo_simulation(params, num_simulations=500)

        return ForecastResult(
            monthly_projections=projections_df,
            annual_summary=annual_summary,
            tax_summary=tax_summary,
            scenario_metrics=metrics,
            risk_analysis=risk_analysis
        )

    def _generate_tax_summary(self, projections_df: pd.DataFrame, params: ScenarioParameters) -> pd.DataFrame:
        """Generate detailed tax summary by year."""
        annual_data = projections_df.groupby(projections_df["month"] // 12).agg({
            "gross_income": "sum",
            "taxes": "sum"
        }).reset_index()

        annual_data["year"] = annual_data["month"] + 1
        annual_data["effective_tax_rate"] = annual_data["taxes"] / annual_data["gross_income"] * 100

        return annual_data[["year", "gross_income", "taxes", "effective_tax_rate"]]

    def _calculate_break_even_years(self, projections_df: pd.DataFrame) -> Optional[float]:
        """Calculate years to break even if scenario results in losses."""
        initial_net_worth = self.current_balances["net_worth"]

        for _, row in projections_df.iterrows():
            if row["net_worth"] >= initial_net_worth:
                return row["year"]

        return None


def create_comprehensive_charts(result: ForecastResult, params: ScenarioParameters) -> List[go.Figure]:
    """Create comprehensive visualization charts for forecast results."""
    charts = []

    # 1. Net Worth Progression with Monte Carlo Bands
    fig_net_worth = go.Figure()

    fig_net_worth.add_trace(go.Scatter(
        x=result.monthly_projections["year"],
        y=result.monthly_projections["net_worth"],
        mode="lines",
        name="Projected Net Worth",
        line=dict(color="blue", width=3)
    ))

    # Add Monte Carlo confidence bands
    if result.risk_analysis:
        # Create bands using percentiles
        years = result.monthly_projections["year"]
        mean_line = result.monthly_projections["net_worth"]

        # Simplified bands based on final volatility (in real implementation, you'd track monthly volatility)
        final_std = result.risk_analysis["std_outcome"]
        upper_band = mean_line + final_std * (years / max(years)) * 0.5
        lower_band = mean_line - final_std * (years / max(years)) * 0.5

        fig_net_worth.add_trace(go.Scatter(
            x=years,
            y=upper_band,
            fill=None,
            mode="lines",
            line_color="rgba(0,0,0,0)",
            showlegend=False
        ))

        fig_net_worth.add_trace(go.Scatter(
            x=years,
            y=lower_band,
            fill="tonexty",
            mode="lines",
            line_color="rgba(0,0,0,0)",
            name="Confidence Band (±1σ)",
            fillcolor="rgba(0,100,80,0.2)"
        ))

    fig_net_worth.update_layout(
        title="Net Worth Projection with Risk Analysis",
        xaxis_title="Years",
        yaxis_title="Net Worth ($)",
        height=500
    )
    charts.append(fig_net_worth)

    # 2. Annual Cash Flow Breakdown
    annual_data = result.monthly_projections.groupby(result.monthly_projections["month"] // 12).agg({
        "gross_income": "sum",
        "expenses": "sum",
        "taxes": "sum",
        "net_cash_flow": "sum"
    }).reset_index()
    annual_data["year"] = annual_data["month"] + 1

    fig_cashflow = go.Figure()
    fig_cashflow.add_trace(go.Bar(x=annual_data["year"], y=annual_data["gross_income"], name="Income", marker_color="green"))
    fig_cashflow.add_trace(go.Bar(x=annual_data["year"], y=-annual_data["expenses"], name="Expenses", marker_color="red"))
    fig_cashflow.add_trace(go.Bar(x=annual_data["year"], y=-annual_data["taxes"], name="Taxes", marker_color="orange"))
    fig_cashflow.add_trace(go.Scatter(x=annual_data["year"], y=annual_data["net_cash_flow"], mode="lines+markers", name="Net Cash Flow", line=dict(color="blue", width=3)))

    fig_cashflow.update_layout(
        title="Annual Cash Flow Analysis",
        xaxis_title="Year",
        yaxis_title="Amount ($)",
        height=500,
        barmode="relative"
    )
    charts.append(fig_cashflow)

    # 3. Tax Analysis Over Time
    fig_tax = make_subplots(specs=[[{"secondary_y": True}]])

    fig_tax.add_trace(
        go.Bar(x=result.tax_summary["year"], y=result.tax_summary["taxes"], name="Total Taxes"),
        secondary_y=False
    )

    fig_tax.add_trace(
        go.Scatter(x=result.tax_summary["year"], y=result.tax_summary["effective_tax_rate"],
                  mode="lines+markers", name="Effective Tax Rate", line=dict(color="red")),
        secondary_y=True
    )

    fig_tax.update_xaxes(title_text="Year")
    fig_tax.update_yaxes(title_text="Tax Amount ($)", secondary_y=False)
    fig_tax.update_yaxes(title_text="Effective Tax Rate (%)", secondary_y=True)
    fig_tax.update_layout(title="Tax Impact Analysis", height=500)

    charts.append(fig_tax)

    return charts