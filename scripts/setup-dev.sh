#!/bin/bash

# Development Environment Setup Script for Generic DynamoDB Repository
# This script sets up a complete development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    print_status "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Found Python $PYTHON_VERSION"
        
        # Check if version is >= 3.9
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
            print_success "Python version is compatible (>= 3.9)"
        else
            print_error "Python 3.9 or higher is required"
            exit 1
        fi
    else
        print_error "Python 3 is not installed"
        exit 1
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
        else
            print_status "Skipping virtual environment creation"
            return 0
        fi
    fi
    
    python3 -m venv venv
    print_success "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Upgrade pip first
    pip install --upgrade pip
    
    # Install package in development mode with all optional dependencies
    pip install -e .[dev,test,docs]
    
    print_success "Dependencies installed"
}

# Setup pre-commit hooks
setup_precommit() {
    print_status "Setting up pre-commit hooks..."
    
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "pre-commit not available, installing..."
        pip install pre-commit
        pre-commit install
        print_success "Pre-commit installed and configured"
    fi
}

# Run initial code quality checks
run_quality_checks() {
    print_status "Running initial code quality checks..."
    
    # Format code
    print_status "Formatting code with Ruff..."
    ruff format .
    
    # Check for linting issues
    print_status "Checking for linting issues..."
    ruff check .
    
    # Run security checks
    print_status "Running security checks..."
    bandit -r generic_repo/ || print_warning "Some security issues found"
    
    print_success "Code quality checks completed"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    # Run unit tests
    pytest tests/ --cov=generic_repo --cov-report=term-missing
    
    print_success "Tests completed"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=("logs" "coverage" "docs/_build")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        fi
    done
}

# Display helpful information
show_info() {
    print_success "Development environment setup complete!"
    echo
    echo -e "${BLUE}Quick Start Commands:${NC}"
    echo "  Activate environment:  source venv/bin/activate"
    echo "  Run tests:            pytest"
    echo "  Format code:          ruff format ."
    echo "  Check linting:        ruff check ."
    echo "  Run example:          python examples/basic_usage.py"
    echo "  Build package:        python -m build"
    echo
    echo -e "${BLUE}Useful Development Commands:${NC}"
    echo "  Install package:      pip install -e ."
    echo "  Run with coverage:    pytest --cov=generic_repo --cov-report=html"
    echo "  Security check:       bandit -r generic_repo/"
    echo "  Type checking:        mypy generic_repo/ (when added)"
    echo
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Configure AWS credentials for integration testing"
    echo "2. Run the examples: python examples/basic_usage.py"
    echo "3. Start developing new features!"
    echo
    echo -e "${GREEN}Happy coding! 🎉${NC}"
}

# Main function
main() {
    echo -e "${BLUE}=== Generic DynamoDB Repository - Development Setup ===${NC}"
    echo
    
    check_python
    create_venv
    activate_venv
    install_dependencies
    create_directories
    setup_precommit
    run_quality_checks
    
    # Ask if user wants to run tests
    read -p "Do you want to run tests now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_tests
    else
        print_status "Skipping tests (you can run them later with 'pytest')"
    fi
    
    show_info
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
else
    print_error "This script should be executed, not sourced"
    return 1
fi 