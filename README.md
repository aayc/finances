# OurFinance 💰

A personal finance dashboard built with Streamlit that integrates with Beancount accounting files.

## Features

- **Income Statement**: Monthly income and expense analysis with interactive charts
- **Balances**: Current account balances with visualizations and net worth tracking
- **Journal**: Transaction history with filtering and search capabilities
- **Forecast**: Financial projections and what-if scenario analysis
- **Accounts**: Detailed account information and management tools

## Setup

1. Set up the development environment:
   ```bash
   make setup
   ```
   This will create a virtual environment and install all dependencies.

2. Configure your Beancount file path:
   ```bash
   cp .env.example .env
   # Edit .env and set BEANCOUNT_FILE to point to your ledger file
   ```

3. Customize account information in the `show_accounts()` function to match your specific accounts.

## Running the App

### Development
```bash
make serve
```

### Production (for TrueNAS)
```bash
make serve-production
```

The app will be available at `http://localhost:8501`

## Makefile Commands

### Development
- `make setup` - Create virtual environment and install dependencies
- `make serve` - Run the application in development mode
- `make serve-production` - Run the application for production deployment
- `make test` - Test that all dependencies are working
- `make install` - Install/update dependencies

### Code Quality
- `make lint` - Run all code quality checks (type checking, formatting, linting)
- `make type-check` - Run type checking with mypy
- `make format` - Format code with black and isort
- `make format-check` - Check code formatting without making changes

### Maintenance
- `make freeze` - Update requirements.txt with current packages
- `make clean` - Remove virtual environment

## Hosting on TrueNAS

To host this on your TrueNAS system:

1. Copy the project files to your TrueNAS system
2. Install Python and pip if not already installed
3. Install the required packages: `pip install -r requirements.txt`
4. Run with: `streamlit run main.py --server.port 8501 --server.address 0.0.0.0`
5. Access via your TrueNAS IP address on port 8501

For Tailscale access, ensure the TrueNAS system is connected to your Tailscale network.

## File Structure

- `main.py` - Main Streamlit application
- `beancount_utils.py` - Beancount data processing utilities
- `style.css` - Custom styling for the UI
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Code Quality & Maintainability

This project uses modern Python development practices:

- **Type Annotations**: Full type coverage with mypy checking
- **Code Formatting**: Black and isort for consistent styling
- **Linting**: Flake8 for code quality checks
- **Documentation**: Comprehensive docstrings with type information
- **Error Handling**: Robust error handling with user-friendly messages

## Customization

- Update account information in the `show_accounts()` function in `main.py`
- Modify the `BEANCOUNT_FILE` path for your ledger location
- Adjust styling in `style.css` for your preferred look
- Add new financial scenarios in the forecast view
- Extend functionality by adding new views or data processing functions in `beancount_utils.py`

## Development

Run code quality checks before committing:
```bash
make lint        # Run all quality checks
make format      # Auto-format code
make type-check  # Check types
```

## Security Note

This application is designed for personal use on a private network. Ensure proper security measures when hosting on any network-accessible system.