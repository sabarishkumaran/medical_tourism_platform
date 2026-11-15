#!/bin/bash
set -e

echo "🚀 Pulling latest code..."
git pull

echo "📦 Rebuilding and restarting containers..."
docker compose up -d --build

echo "✅ Deployment complete! Viewing logs (press Ctrl+C to exit)..."
docker compose logs -f
