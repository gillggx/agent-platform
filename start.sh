#!/bin/bash

# Multi-Agent Collaboration Platform - Startup Script

echo "🚀 Starting Multi-Agent Collaboration Platform..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file and set your LLM_API_KEY"
    echo "   Example: LLM_API_KEY=sk-your-openai-api-key-here"
    echo ""
    read -p "Press Enter after setting your LLM API key in .env file..."
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Initialize database
echo "🗄️ Initializing database..."
docker-compose exec -T api python init_db.py

# Run system test
echo "🧪 Running system tests..."
docker-compose exec -T api python -c "
import sys
sys.path.append('/app')
import asyncio
from test_system import main
asyncio.run(main())
" 2>/dev/null || python3 test_system.py

echo ""
echo "🎉 Startup complete!"
echo ""
echo "🌐 Access the platform:"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Health:   http://localhost:8000/health"
echo ""
echo "📚 Demo Account:"
echo "   Email:    demo@example.com"
echo "   Password: demo123"
echo ""
echo "🛑 To stop all services: docker-compose down"