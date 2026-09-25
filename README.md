
## Summary

This README provides:

1. **Complete setup instructions** with Python version requirements, dependency installation, and environment configuration
2. **Step-by-step demo path** showing:
   - How to start the demo app
   - Exact discovery command with expected output
   - Exact replay command with different parameters
3. **Running without live services** via headless mode, saved artifacts, or static HTML
4. **Troubleshooting section** addressing common issues from your conversation history
5. **Project structure** for easy navigation
6. **Advanced usage** for customization

The README is production-ready and includes all necessary information for someone to clone, set up, and run the system successfully.

### ################################# ###
## Prerequisite 
- **Python 3.14** (required )
- **Anthropic API Key** (for Claude 3.5 Sonnet)
- **Google Chrome** (optional - uses Playwright's Chromium by default)
- **macOS, Linux, or Windows** (tested on macOS)

### ################################# ###
## Setup

### 1. Clone the Repository

git clone <your-repo-url>
cd pi-agents-exercise

### 2. Create virtual environment
# Ensure you're using Python 3.14
python --version  # Should show Python 3.14

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

### 3. Install dependencies 

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

### 4. configure environment variables
# Copy example (if available)
cp .env.example .env

# Copy example (if available)
cp .env.example .env

# OR create manually
touch .envtouch .env

# update API key - see sample env file 
ANTHROPIC_API_KEY = our-actual-key-here


# Test Python imports
python -c "from anthropic import Anthropic; from playwright.async_api import async_playwright; print('✅ All dependencies installed')"

# Test environment variables
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ API Key loaded' if os.getenv('ANTHROPIC_API_KEY') else '❌ API Key missing')"


### ################################# ###
### 5.  Running the Demo application (test) - dont terminate the process. 
# Start demo app
python demo_app/app.py

you could see  
* Running on http://127.0.0.1:5000

Verify the app is running: Open http://localhost:5000 in your browser. You should see the banking application landing page.

Available test members:
Member ID: 12345 (John Doe)
Member ID: 67890 (Jane Smith)

### ################################# ###
### 6.  Run Discovery (Learn a New Capability) 
python -m src.main discover \
  --goal "Look up member 12345 and read their savings balance" \
  --entry-point "  --entry-point "http://127.0.0.1:5000/search" \
  --parameters '{"member_id": "12345"}'

# What happens:
1. Browser window opens (non-headless by default)
2. Agent navigates to the search page
3. Claude analyzes the UI and decides actions
4. Agent fills in member ID and clicks search
5. Agent extracts the savings balance
6. Capability artifact is saved to artifacts/ directory 

# Expected console output
🔍 Starting discovery: Look up member 12345 and read their savings balance
📍 Entry point: http://localhost:5000/search

✅ Browser launched successfully (attempt 1/3)
[Discovery steps execute...]

✅ Discovery complete!
📄 Artifact saved: artifacts/cap_http:__127.0.0.1:5000_search_3.json
📊 Result: success
📁 Evidence: evidence/discovery_cap_http:__127.0.0.1:5000_search_3.json

🎯 Outputs: {
  "member_id": "12345",
  "member_name": "John Doe",
  "savings_balance": "$5,432.10"
}


### ################################# ###
### 7.  Replay the Capability (Deterministic Execution)
python -m src.main replay \
  --artifact artifacts/cap_http:__127.0.0.1:5000_search_3.json \
  --parameters '{"member_id": "12345"}'

# What happens:
1. Loads the saved artifact
2. Executes steps deterministically (no LLM calls)
3. Substitutes the new member ID parameter
4. Extracts outputs using the learned pattern

# Expected output:
▶️  Starting replay: artifacts/cap_http:__127.0.0.1:5000_search_3.json
📋 Capability: Look up member 12345 and read their savings balance
📥 Parameters: {
  "member_id": "67890"
}

✅ Browser launched successfully (attempt 1/3)
[Replay steps execute...]

✅ Replay complete!
📊 Status: success
📁 Evidence: evidence/replay_cap_http:__127.0.0.1:5000_search_3_<execution_id>.json

🎯 Outputs: {
  "member_id": "67890",
  "member_name": "Jane Smith",
  "savings_balance": "$12,345.67"
}

### Running Without Live Services

# Option 1: Use Saved Artifacts (No LLM Required)
# Replay uses only the artifact, no LLM calls
python -m src.main replay \
  --artifact artifacts/cap_http:__127.0.0.1:5000_search_3.json \
  --parameters '{"member_id": "12345"}'

# Option 2: Headless Mode (No Browser UI)
# Discovery in headless mode
python -m src.main discover \
  --goal "Look up member 12345 and read their savings balance" \
  --entry-point "http://localhost:5000/search" \
  --parameters '{"member_id": "12345"}' \
  --headless

# Replay in headless mode
python -m src.main replay \
  --artifact artifacts/cap_http:__127.0.0.1:5000_search_3.json \
  --parameters '{"member_id": "67890"}' \
  --headless

### Troubleshooting
Browser Crashes on Launch
Symptom: Browser.new_page: Target crashed

Solution: Ensure you're using Python 3.14:

python --version  # Should show 3.12.x

# If wrong version, recreate venv
deactivate
rm -rf venv
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# API Key Not Found
API Key Not Found
# Check .env exists and has key
cat .env | grep ANTHROPIC_API_KEY

# Test loading
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ANTHROPIC_API_KEY')[:20] + '...')"

# Artifact Deserialization Error
# Delete old artifacts
rm -rf artifacts/*.json

# Run discovery again
python -m src.main discover \
  --goal "Look up member 12345 and read their savings balance" \
  --entry-point "http://localhost:5000/search" \
  --parameters '{"member_id": "12345"}'

# you can run this in firefox or webkit,provided that you install required libarary/plugins   