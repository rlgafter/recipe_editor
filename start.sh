#!/bin/bash
# Recipe Editor - Start Script

echo "================================"
echo "Recipe Editor - Starting Server"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Virtual environment created."
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Dependencies not installed. Installing from requirements.txt..."
    pip install -r requirements.txt
    echo "Dependencies installed."
    echo ""
fi

# Start the application
echo "Starting Recipe Editor..."
echo "Access the application at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

python app.py

