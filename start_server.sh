#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

echo "🚀 Starting Gemini CLI API Server..."
echo "📁 Working directory: $(pwd)"
echo "🐍 Python version: $(python3 --version)"
echo "🔧 Gemini CLI path: $(which gemini)"

# Check if gemini CLI is available
if ! command -v gemini &> /dev/null; then
    echo "❌ Error: 'gemini' command not found in PATH"
    echo "Please install gemini-cli first: https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/cli"
    exit 1
fi

# Test gemini CLI
echo "🧪 Testing gemini CLI..."
if gemini --version &> /dev/null; then
    echo "✅ Gemini CLI test successful"
else
    echo "⚠️ Gemini CLI test failed, but continuing anyway"
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export CONSOLE_OUTPUT_ENABLED=true
export CONSOLE_OUTPUT_VERBOSE=true
export DEBUG_DUMP_ENABLED=true

echo "🌐 Starting server on http://localhost:${PORT:-8000}"
echo "📊 API docs available at http://localhost:${PORT:-8000}/docs"
echo "❤️ Health check at http://localhost:${PORT:-8000}/health"

# Start the FastAPI server using uvicorn from the virtual environment
./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload

echo "🛑 Server stopped."