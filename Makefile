# OurFinance Makefile

# Variables
VENV_DIR = venv
PYTHON = python3
PIP = $(VENV_DIR)/bin/pip
PYTHON_VENV = $(VENV_DIR)/bin/python
STREAMLIT = $(VENV_DIR)/bin/streamlit

# Default target
.PHONY: help
help:
	@echo "OurFinance Development Commands:"
	@echo "  make setup        - Create virtual environment and install dependencies"
	@echo "  make serve        - Run the Streamlit application"
	@echo "  make install      - Install/update dependencies"
	@echo "  make clean        - Remove virtual environment"
	@echo "  make test         - Test the application setup"
	@echo "  make freeze       - Update requirements.txt with current packages"
	@echo "  make lint         - Run all code quality checks"
	@echo "  make type-check   - Run type checking with mypy"
	@echo "  make format       - Format code with black and isort"
	@echo "  make format-check - Check code formatting without making changes"

# Create virtual environment and install dependencies
.PHONY: setup
setup: $(VENV_DIR)/bin/activate
	@echo "✅ Virtual environment created and dependencies installed!"
	@echo "To activate manually: source $(VENV_DIR)/bin/activate"

$(VENV_DIR)/bin/activate: requirements.txt
	@echo "🔧 Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "📦 Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV_DIR)/bin/activate

# Install/update dependencies
.PHONY: install
install: $(VENV_DIR)/bin/activate
	@echo "📦 Installing/updating dependencies..."
	$(PIP) install -r requirements.txt

# Run the Streamlit application
.PHONY: serve
serve: $(VENV_DIR)/bin/activate
	@echo "🚀 Starting OurFinance application..."
	@echo "Access at: http://localhost:8501"
	$(STREAMLIT) run main.py

# Test the application setup
.PHONY: test
test: $(VENV_DIR)/bin/activate
	@echo "🧪 Testing application setup..."
	$(PYTHON_VENV) -c "import streamlit; print('✅ Streamlit imported successfully')"
	$(PYTHON_VENV) -c "import pandas; print('✅ Pandas imported successfully')"
	$(PYTHON_VENV) -c "import plotly; print('✅ Plotly imported successfully')"
	$(PYTHON_VENV) -c "import beancount; print('✅ Beancount imported successfully')"
	$(PYTHON_VENV) -c "import beancount_utils; print('✅ Beancount utils imported successfully')"
	@echo "🎉 All dependencies are working correctly!"

# Update requirements.txt with current packages
.PHONY: freeze
freeze: $(VENV_DIR)/bin/activate
	@echo "📋 Updating requirements.txt..."
	$(PIP) freeze > requirements.txt

# Clean up virtual environment
.PHONY: clean
clean:
	@echo "🧹 Removing virtual environment..."
	rm -rf $(VENV_DIR)
	@echo "✅ Virtual environment removed!"

# Production serve (for TrueNAS deployment)
.PHONY: serve-production
serve-production: $(VENV_DIR)/bin/activate
	@echo "🚀 Starting OurFinance in production mode..."
	@echo "Access at: http://0.0.0.0:8501"
	$(STREAMLIT) run main.py --server.port 8501 --server.address 0.0.0.0

# Code quality checks
.PHONY: lint
lint: $(VENV_DIR)/bin/activate
	@echo "🔍 Running code quality checks..."
	$(VENV_DIR)/bin/flake8 *.py
	$(VENV_DIR)/bin/black --check *.py
	$(VENV_DIR)/bin/isort --check-only *.py
	$(VENV_DIR)/bin/mypy *.py
	@echo "✅ All code quality checks passed!"

# Type checking
.PHONY: type-check
type-check: $(VENV_DIR)/bin/activate
	@echo "🔍 Running type checks..."
	$(VENV_DIR)/bin/mypy *.py
	@echo "✅ Type checking completed!"

# Format code
.PHONY: format
format: $(VENV_DIR)/bin/activate
	@echo "🎨 Formatting code..."
	$(VENV_DIR)/bin/black *.py
	$(VENV_DIR)/bin/isort *.py
	@echo "✅ Code formatting completed!"

# Check formatting without changes
.PHONY: format-check
format-check: $(VENV_DIR)/bin/activate
	@echo "🔍 Checking code formatting..."
	$(VENV_DIR)/bin/black --check *.py
	$(VENV_DIR)/bin/isort --check-only *.py
	@echo "✅ Code formatting check completed!"