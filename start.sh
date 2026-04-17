#!/bin/bash

# 에러 발생 시 스크립트 중단 설정
set -e

COMPOSE_CMD="docker compose"
if ! docker compose version > /dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
fi

echo "🚀 Starting 'Ask What Matters — HB Presents'..."

# 1. Environment Variable Check
if [ ! -f ./backend/.env ]; then
    echo "⚠️  backend/.env file not found. Copying from .env.example..."
    cp ./backend/.env.example ./backend/.env
    echo "👉 ACTION REQUIRED: Please add your OpenAI API Key to backend/.env"
fi

if [ ! -f ./frontend/.env ]; then
    echo "⚠️  frontend/.env file not found. Copying from .env.example..."
    cp ./frontend/.env.example ./frontend/.env
fi

# 2. Docker Daemon Check
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker daemon is not running."
    echo "Please start Docker and try again."
    exit 1
fi

# 3. Run Docker Compose
echo "📦 Building and starting Docker containers..."
if $COMPOSE_CMD up --build -d; then
    echo ""
    echo "✅ Deployment Successful!"
    echo "🌐 App: http://localhost"
    echo "⚙️  API Health: http://localhost/health"
    echo "📝 To view logs, run: '$COMPOSE_CMD logs -f'"
else
    echo ""
    echo "❌ Error: Docker Compose failed to start."
    echo "Please check the error messages above."
    exit 1
fi

echo "------------------------------------------------"
echo "Note: If the app fails to fetch questions, ensure your"
echo "OPENAI_API_KEY is correctly set in backend/.env"
echo "------------------------------------------------"
