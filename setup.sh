#!/bin/bash

echo "🚀 Setting up Computer-Use Automation System..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create directories
mkdir -p artifacts
mkdir -p evidence/screenshots

# Copy environment template
if [ ! -f .env ]; then
cp .env.example .env
echo "⚠️  Please edit .env and add your ANTHROPIC_API_KEY"
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your ANTHROPIC_API_KEY"
echo "2. Start demo app: python demo_app/app.py"
echo "3. Run discovery: python -m src.main discover --goal '...' --entry-point 'http://localhost:5000/search'"
