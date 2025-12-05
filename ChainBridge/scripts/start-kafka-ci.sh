#!/bin/bash
set -e

echo "🚀 Starting Kafka CI Harness..."

# Start services
docker compose -f docker-compose.kafkaci.yml up -d

echo "⏳ Waiting for Kafka to be ready..."

# Wait for Kafka healthcheck
timeout=60
elapsed=0
while ! docker compose -f docker-compose.kafkaci.yml exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; do
    sleep 2
    elapsed=$((elapsed + 2))
    if [ $elapsed -gt $timeout ]; then
        echo "❌ Kafka failed to start within $timeout seconds"
        docker compose -f docker-compose.kafkaci.yml logs
        exit 1
    fi
    echo "Still waiting... ($elapsed/$timeout)"
done

echo "✅ Kafka is ready!"

# Print topic summary
echo "📋 Current topics:"
docker compose -f docker-compose.kafkaci.yml exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list

echo "🎯 Kafka CI Harness ready at localhost:29092"
