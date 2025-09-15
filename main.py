import os
from typing import Any, Dict, List, Tuple

import streamlit as st
from beancount import loader
from beancount.core import data

import beancount_utils as bc_utils
from views.income_statement import show_income_statement
from views.balances import show_balances
from views.journal import show_journal
from views.forecast import show_forecast
from views.accounts import show_accounts

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

    # Get current page from URL query parameter
    query_params = st.query_params
    current_page_from_url = query_params.get("page", "Income Statement")

    # Ensure the page from URL is valid
    pages = list(PAGE_TITLES.keys())
    if current_page_from_url not in pages:
        current_page_from_url = "Income Statement"

    # Find the index for the current page
    try:
        current_page_index = pages.index(current_page_from_url)
    except ValueError:
        current_page_index = 0

    # Sidebar navigation with vertical tabs
    page = st.sidebar.radio(
        "Navigation",
        pages,
        format_func=lambda x: PAGE_TITLES[x],
        label_visibility="collapsed",
        index=current_page_index
    )

    # Update URL when page changes
    if page != current_page_from_url:
        st.query_params.page = page

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



if __name__ == "__main__":
    main()
