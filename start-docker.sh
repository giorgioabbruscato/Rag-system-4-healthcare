#!/bin/bash

# RAG Healthcare System - Startup Script
# Automatically starts all Docker services

set -e

echo "🚀 RAG Healthcare System - Startup"
echo "===================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Start Docker Desktop."
    exit 1
fi

echo "✅ Docker is running"

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found"
    exit 1
fi

echo "✅ docker-compose found"

# Check .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "📝 IMPORTANT: Edit the .env file and add your OPENAI_API_KEY"
    echo "   Run: nano .env"
    echo ""
    read -p "Press ENTER after configuring .env, or CTRL+C to exit..."
fi

echo "✅ .env file found"
echo ""

# Stop existing containers
echo "🧹 Cleaning existing containers..."
docker-compose down 2>/dev/null || true
echo ""

# Build images
echo "🏗️  Building Docker images..."
docker-compose build --no-cache
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
echo ""

MAX_WAIT=120
WAITED=0

# Wait for Qdrant
echo -n "   📦 Qdrant: "
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:6333/health &> /dev/null; then
        echo "✅ Ready"
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Timeout"
    echo "View logs: docker-compose logs qdrant"
    exit 1
fi

# Wait for API
WAITED=0
echo -n "   🔧 API Backend: "
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/list-docs?rag_type=cases &> /dev/null; then
        echo "✅ Ready"
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Timeout"
    echo "View logs: docker-compose logs api"
    exit 1
fi

# Wait for Streamlit
WAITED=0
echo -n "   🎨 Streamlit Frontend: "
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8501/_stcore/health &> /dev/null; then
        echo "✅ Ready"
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Timeout"
    echo "View logs: docker-compose logs streamlit"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ All services are running!"
echo "============================================"
echo ""
echo "📍 Access services:"
echo ""
echo "   🎨 Streamlit UI:    http://localhost:8501"
echo "   🔧 API Backend:     http://localhost:8000"
echo "   📚 API Docs:        http://localhost:8000/docs"
echo "   📦 Qdrant DB:       http://localhost:6333/dashboard"
echo ""
echo "💡 Useful commands:"
echo ""
echo "   make docker-logs         # View logs"
echo "   make docker-ps           # View status"
echo "   ./stop-docker.sh         # Stop everything"
echo ""
echo "============================================"
