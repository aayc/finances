import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import beancount_utils as bc_utils
from views.financial_health import show_financial_health
from views.income_statement import show_income_statement
from views.balances import show_balances
from views.journal import show_journal
from views.forecast import show_forecast
from views.accounts import show_accounts

st.set_page_config(
    page_title="Finances", page_icon="💰", layout="wide", initial_sidebar_state="expanded"
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

# Configuration - Year for Azure beancount file loading
BEANCOUNT_YEAR: str = os.environ.get("BEANCOUNT_YEAR", "2025")

# UI Constants
PAGE_TITLES = {
    "Financial Health": "🏥 Financial Health",
    "Income Statement": "📈 Income Statement",
    "Balances": "⚖️ Balance Report",
    "Journal": "📔 Transaction Journal",
    "Forecast": "🔮 Financial Forecast",
    "Accounts": "🏦 Account Information",
}

PAGE_DESCRIPTIONS = {
    "Financial Health": "Comprehensive dashboard of your financial well-being and health metrics.",
    "Income Statement": "View your monthly income and expenses with interactive charts.",
    "Balances": "Check current balances across all your accounts.",
    "Journal": "Browse and filter your transaction history.",
    "Forecast": "Run what-if scenarios for major financial decisions.",
    "Accounts": "Access detailed information about all your accounts.",
}




def main() -> None:
    """Main application entry point."""

    # Get current page from URL query parameter
    query_params = st.query_params
    current_page_from_url = query_params.get("page", "Financial Health")

    # Ensure the page from URL is valid
    pages = list(PAGE_TITLES.keys())
    if current_page_from_url not in pages:
        current_page_from_url = "Financial Health"

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

    # Load data from Azure File Share
    entries, errors, options_map = bc_utils.load_beancount_data(BEANCOUNT_YEAR)

    if not entries:
        st.error(
            "No data loaded from Azure File Share. Please check your Azure configuration and ensure the beancount file exists."
        )
        st.stop()  # Stop execution instead of return for better UX

    # Route to different pages
    if page == "Financial Health":
        show_financial_health(entries, options_map)
    elif page == "Income Statement":
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
