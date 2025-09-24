"""Account Information view for Finances."""

import streamlit as st
import pandas as pd


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
        "💻 **Customization Note:** Update the account information in the `show_accounts()` function in views/accounts.py to match your specific accounts and institutions."
    )