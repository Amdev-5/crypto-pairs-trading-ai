#!/bin/bash

# Pairs Trading System - Quick Run Script

echo "============================================================"
echo "CRYPTO PAIRS TRADING SYSTEM"
echo "============================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found!"
    echo "Please run setup first:"
    echo "  python3 setup.py"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Please configure your API keys in .env"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import pybit" 2>/dev/null; then
    echo "⚠️  Dependencies not installed!"
    echo "Installing now..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ Environment ready"
echo ""
echo "Starting trading engine..."
echo "Press Ctrl+C to stop"
echo ""
echo "============================================================"
echo ""

# Run the trading engine
python -m src.main

# Deactivate on exit
deactivate
