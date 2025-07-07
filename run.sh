#!/bin/bash

# AskMe Application Runner

echo "🚀 Starting AskMe Application..."
echo "=================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/lib/python*/site-packages/Flask" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "📋 Application Information:"
echo "- User Interface: http://localhost:5000"
echo "- Admin Interface: http://localhost:5000/admin/login"
echo "- Admin Credentials: admin / admin123"
echo ""
echo "Press Ctrl+C to stop the application"
echo "=================================="
echo ""

# Run the application
python app.py
