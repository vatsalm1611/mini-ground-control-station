#!/bin/bash
# Local run script for Mini GCS backend

echo "Setting up Python virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To run the server:"
echo "  export SIM_MODE=SIM"
echo "  export TELEMETRY_RATE=5"
echo "  python -m app.server"
echo ""
