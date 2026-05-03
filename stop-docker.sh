#!/bin/bash

# RAG Healthcare System - Shutdown Script
# Automatically stops all Docker services

set -e

echo "🛑 RAG Healthcare System - Shutdown"
echo "===================================="
echo ""

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "ℹ️  No active services"
    exit 0
fi

echo "🔍 Active services:"
docker-compose ps
echo ""

# Ask for confirmation
read -p "⚠️  Do you want to stop all services? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "🛑 Stopping services..."
echo ""

# Stop containers
docker-compose stop

echo ""
echo "🗑️  Removing containers..."
docker-compose down

echo ""
echo "============================================"
echo "✅ All services have been stopped"
echo "============================================"
echo ""
echo "💡 Data has been preserved in Docker volumes"
echo ""
echo "   To restart:             ./start-docker.sh"
echo "   To clean everything:    make docker-clean"
echo ""
