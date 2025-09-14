This project is called OurFinance. Here is the spec for the project:

My wife and I meticulously track our finances using the Beancount system. The beancount file is stored at "/Users/aaronchan/Projects/Aaron Chan Vault/Ledgers/2025.beancount". We'd like to have a shared web app where we can view how we're doing each month with respect to budgeting, expenses and income for that month. We want to see summary tables and graphs. We also want a journal tab where we can see the transactions and filter by account. Lastly, it would be nice to do some sort of simulation, like what if we buy a house.

We'll be hosting this website as simply as possible on our TrueNAS computer, which we can access via Tailscale. Since this is just for us and beancount libraries are in python, I think streamlit app makes the most sense.

This is also a great place to keep/hardcode information about our asset accounts. I have many accounts as can be seen in the beancount file and my wife needs to know about the accounts, how much is in them, where to go to access them etc. I think this should be yet a separate tab.

In summary, OurFinance is a streamlit app that should have separate views - income statement, balances, journal, forecast, accounts. It should be beautiful, fast, and interactive.