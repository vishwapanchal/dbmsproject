#!/bin/bash

# 1. Get the directory where this script is located (backend/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 2. Go to the backend folder
cd "$SCRIPT_DIR"

# 3. Activate the Virtual Environment
# We look for .venv in the parent directory (TRUEPROJECT/.venv)
if [ -f "../.venv/Scripts/activate" ]; then
    echo "🔋 Activating Windows Virtual Environment..."
    source "../.venv/Scripts/activate"
elif [ -f "../.venv/bin/activate" ]; then
    echo "🔋 Activating Linux/Mac Virtual Environment..."
    source "../.venv/bin/activate"
else
    echo "⚠️  .venv not found! Trying to run with global Python..."
fi

# 4. Run the API Server
echo "🚀 Starting AI Test API..."
python test_ai_api.py