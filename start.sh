#!/bin/bash
# Quick start script for local development

echo "================================"
echo "LinkedIn AI Manager - Quick Start"
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python init_db.py

# Run combined server
echo ""
echo "================================"
echo "Starting LinkedIn AI Manager..."
echo "================================"
echo ""
echo "Dashboard will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python run_all.py
