import calendar
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import streamlit as st
from beancount.core import amount as amount_lib
from beancount.core import data, getters, inventory, realization
from beancount.core.number import D

# Constants
ACCOUNT_TYPES = {
    "ASSETS": "Assets:",
    "LIABILITIES": "Liabilities:",
    "INCOME": "Income:",
    "EXPENSES": "Expenses:",
    "EQUITY": "Equity:",
}

DEFAULT_CURRENCY = "USD"


def get_monthly_income_statement(
    entries: List[data.Directive],
    options_map: Dict[str, Any],
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Get income statement data for a specific month or year.

    Args:
        entries: List of beancount entries
        options_map: Beancount options map
        year: Target year (defaults to current year)
        month: Target month (optional, if None shows all months for year)

    Returns:
        Tuple of (income_df, expense_df) DataFrames
    """
    if year is None:
        year = datetime.now().year

    income_data: List[Dict[str, Union[str, float]]] = []
    expense_data: List[Dict[str, Union[str, float]]] = []

    # Process transactions directly
    for entry in entries:
        if isinstance(entry, data.Transaction):
            # Filter by date
            if entry.date.year != year:
                continue
            if month and entry.date.month != month:
                continue

            for posting in entry.postings:
                if posting.account and posting.units:
                    account = posting.account
                    currency = posting.units.currency
                    amount = float(posting.units.number or 0)

                    entry_data: Dict[str, Union[str, float]] = {
                        "account": account,
                        "currency": currency,
                        "amount": amount,
                    }

                    if account.startswith(ACCOUNT_TYPES["INCOME"]):
                        income_data.append(entry_data)
                    elif account.startswith(ACCOUNT_TYPES["EXPENSES"]):
                        expense_data.append(entry_data)

    income_df = pd.DataFrame(income_data)
    expense_df = pd.DataFrame(expense_data)

    # Group by account and currency, summing amounts
    if len(income_df) > 0:
        income_df = income_df.groupby(["account", "currency"], as_index=False)["amount"].sum()
    if len(expense_df) > 0:
        expense_df = expense_df.groupby(["account", "currency"], as_index=False)["amount"].sum()

    return income_df, expense_df


@st.cache_data
def get_account_balances(
    _entries: List[data.Directive], _options_map: Dict[str, Any], as_of_date: Optional[date] = None
) -> pd.DataFrame:
    """Get current account balances as of a specific date.

    Args:
        _entries: List of beancount entries (prefixed with _ for caching)
        options_map: Beancount options map
        as_of_date: Date to calculate balances as of (defaults to today)

    Returns:
        DataFrame with columns: account, currency, amount
    """
    if as_of_date is None:
        as_of_date = datetime.now().date()

    # Filter entries up to the specified date
    filtered_entries = [entry for entry in _entries if entry.date <= as_of_date]

    # Get real accounts
    real_root = realization.realize(filtered_entries)

    balances: List[Dict[str, Union[str, float]]] = []

    def extract_balances(account_node: Any, account_name: str = "") -> None:
        if account_node.balance is not None and not account_node.balance.is_empty():
            for position in account_node.balance:
                balances.append(
                    {
                        "account": account_name or account_node.account,
                        "currency": position.units.currency,
                        "amount": float(position.units.number),
                    }
                )

        for child_name, child_node in account_node.items():
            child_account = f"{account_name}:{child_name}" if account_name else child_name
            extract_balances(child_node, child_account)

    extract_balances(real_root)
    balances_df = pd.DataFrame(balances)

    # Filter out zero or near-zero balances
    if len(balances_df) > 0:
        balances_df = balances_df[abs(balances_df["amount"]) > 0.01]

    return balances_df


def get_transactions(
    entries: List[data.Directive],
    options_map: Dict[str, Any],
    account_filter: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Get transaction data with optional filtering.

    Args:
        entries: List of beancount entries
        options_map: Beancount options map
        account_filter: Filter transactions by account name (partial match)
        start_date: Earliest transaction date to include
        end_date: Latest transaction date to include

    Returns:
        DataFrame with transaction details
    """
    transactions: List[Dict[str, Any]] = []

    for entry in entries:
        if isinstance(entry, data.Transaction):
            # Date filtering
            if start_date and entry.date < start_date:
                continue
            if end_date and entry.date > end_date:
                continue

            for posting in entry.postings:
                # Account filtering
                if account_filter and account_filter not in posting.account:
                    continue

                if posting.units:
                    transactions.append(
                        {
                            "date": entry.date,
                            "account": posting.account,
                            "description": entry.narration,
                            "currency": posting.units.currency,
                            "amount": float(posting.units.number or 0),
                            "payee": getattr(entry, "payee", ""),
                            "tags": list(entry.tags) if entry.tags else [],
                            "links": list(entry.links) if entry.links else [],
                        }
                    )

    transactions_df = pd.DataFrame(transactions)

    if len(transactions_df) > 0:
        transactions_df = transactions_df.sort_values("date", ascending=False)
        # Convert date column to datetime if it isn't already
        transactions_df["date"] = pd.to_datetime(transactions_df["date"])

    return transactions_df


def get_account_hierarchy(entries: List[data.Directive]) -> Dict[str, List[str]]:
    """Get the account hierarchy for display purposes.

    Args:
        entries: List of beancount entries

    Returns:
        Dictionary mapping parent accounts to lists of child accounts
    """
    all_accounts = getters.get_accounts(entries)
    hierarchy: defaultdict[str, List[str]] = defaultdict(list)

    for account in sorted(all_accounts):
        parts = account.split(":")
        if len(parts) > 1:
            parent = ":".join(parts[:-1])
            hierarchy[parent].append(account)
        else:
            hierarchy["Root"].append(account)

    return dict(hierarchy)


def get_monthly_trends(
    entries: List[data.Directive],
    options_map: Dict[str, Any],
    account_pattern: str,
    months_back: int = 12,
) -> pd.DataFrame:
    """Get monthly trends for specific account patterns.

    Args:
        entries: List of beancount entries
        options_map: Beancount options map
        account_pattern: Pattern to match accounts (e.g., 'Income:', 'Expenses:')
        months_back: Number of months to look back

    Returns:
        DataFrame with monthly trend data
    """
    current_date = datetime.now()
    trends: List[Dict[str, Union[str, int, float, date]]] = []

    for i in range(months_back):
        # Calculate month and year
        month = current_date.month - i
        year = current_date.year

        if month <= 0:
            month += 12
            year -= 1

        # Calculate total amount for the month
        total_amount: float = 0

        for entry in entries:
            if isinstance(entry, data.Transaction):
                if entry.date.year == year and entry.date.month == month:
                    for posting in entry.postings:
                        if posting.account and posting.units:
                            if posting.account.startswith(account_pattern):
                                total_amount += float(posting.units.number or 0)

        trends.append(
            {
                "year": year,
                "month": month,
                "month_name": calendar.month_abbr[month],
                "amount": total_amount,
                "date": date(year, month, 1),
            }
        )

    return pd.DataFrame(trends).sort_values("date")


def categorize_accounts(accounts: List[str]) -> Dict[str, List[str]]:
    """Categorize accounts for better organization.

    Args:
        accounts: List of account names

    Returns:
        Dictionary mapping category names to lists of accounts
    """
    categories: Dict[str, List[str]] = {
        "Assets": [],
        "Liabilities": [],
        "Income": [],
        "Expenses": [],
        "Equity": [],
    }

    for account in accounts:
        if account.startswith(ACCOUNT_TYPES["ASSETS"]):
            categories["Assets"].append(account)
        elif account.startswith(ACCOUNT_TYPES["LIABILITIES"]):
            categories["Liabilities"].append(account)
        elif account.startswith(ACCOUNT_TYPES["INCOME"]):
            categories["Income"].append(account)
        elif account.startswith(ACCOUNT_TYPES["EXPENSES"]):
            categories["Expenses"].append(account)
        elif account.startswith(ACCOUNT_TYPES["EQUITY"]):
            categories["Equity"].append(account)

    return categories


def get_available_months_with_data(entries: List[data.Directive], year: int) -> List[int]:
    """Get list of months that have transaction data for a given year.

    Args:
        entries: List of beancount entries
        year: Year to check for data

    Returns:
        List of month numbers (1-12) that have data
    """
    months_with_data = set()

    for entry in entries:
        if isinstance(entry, data.Transaction) and entry.date.year == year:
            for posting in entry.postings:
                if posting.account and posting.units:
                    if posting.account.startswith(
                        ACCOUNT_TYPES["INCOME"]
                    ) or posting.account.startswith(ACCOUNT_TYPES["EXPENSES"]):
                        months_with_data.add(entry.date.month)

    return sorted(list(months_with_data))


def get_budget_data(entries: List[data.Directive], options_map: Dict[str, Any]) -> Dict[str, Any]:
    """Extract budget information from beancount entries.

    Args:
        entries: List of beancount entries
        options_map: Beancount options map

    Returns:
        Dictionary containing budget data organized by account
    """
    budgets = {}

    # Look for budget entries in the beancount file
    for entry in entries:
        if isinstance(entry, data.Custom) and entry.type == "budget":
            # Parse budget entries - format: 2025-01-01 custom "budget" Expenses:Joint:Dining "monthly" 200.00 USD
            if len(entry.values) >= 3:
                # Extract account name from ValueType
                account = entry.values[0].value if hasattr(entry.values[0], "value") else str(entry.values[0])

                # Extract frequency from ValueType
                frequency = entry.values[1].value if hasattr(entry.values[1], "value") else str(entry.values[1])

                # Extract amount and currency from ValueType containing Amount
                amount_value = entry.values[2].value if hasattr(entry.values[2], "value") else entry.values[2]

                if hasattr(amount_value, "number") and hasattr(amount_value, "currency"):
                    amount = float(amount_value.number)
                    currency = amount_value.currency
                else:
                    # Fallback parsing if format is different
                    try:
                        amount_str = str(amount_value)
                        parts = amount_str.split()
                        amount = float(parts[0])
                        currency = parts[1] if len(parts) > 1 else "USD"
                    except (ValueError, IndexError):
                        continue

                # Handle different budget frequencies
                if frequency == "monthly":
                    # Apply budget to all months of the year
                    year = entry.date.year
                    for month in range(1, 13):
                        year_month = f"{year}-{month:02d}"

                        if year_month not in budgets:
                            budgets[year_month] = {}

                        budgets[year_month][account] = {
                            "amount": amount,
                            "currency": currency,
                            "date": entry.date,
                            "frequency": frequency
                        }

                elif frequency == "yearly":
                    # Store yearly budgets separately - don't break them down to monthly
                    year = entry.date.year
                    year_key = f"{year}-yearly"

                    if year_key not in budgets:
                        budgets[year_key] = {}

                    budgets[year_key][account] = {
                        "amount": amount,
                        "currency": currency,
                        "date": entry.date,
                        "frequency": frequency
                    }

    return budgets
