# docker_redis_setup.ps1
# Run this in PowerShell (not WSL)

Write-Host "🐳 Setting up Redis with Docker..." -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running or not installed" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Start Redis container
Write-Host "🚀 Starting Redis container..." -ForegroundColor Blue
docker run --name music-legends-redis -p 6379:6379 -d redis:7-alpine

# Wait for Redis to start
Write-Host "⏳ Waiting for Redis to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Test Redis connection
Write-Host "🧪 Testing Redis connection..." -ForegroundColor Blue
try {
    $result = docker exec music-legends-redis redis-cli ping
    if ($result -eq "PONG") {
        Write-Host "✅ Redis is working!" -ForegroundColor Green
        Write-Host "🎉 Your bot can now connect to Redis on localhost:6379" -ForegroundColor Green
    } else {
        Write-Host "❌ Redis test failed: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Failed to test Redis: $_" -ForegroundColor Red
}

Write-Host "`n📋 Redis Management Commands:" -ForegroundColor Cyan
Write-Host "• Stop Redis: docker stop music-legends-redis" -ForegroundColor White
Write-Host "• Start Redis: docker start music-legends-redis" -ForegroundColor White
Write-Host "• Remove Redis: docker rm music-legends-redis" -ForegroundColor White
Write-Host "• View logs: docker logs music-legends-redis" -ForegroundColor White
Write-Host "• Test connection: docker exec music-legends-redis redis-cli ping" -ForegroundColor White

Write-Host "`n🚀 Now run your bot: python main.py" -ForegroundColor Green
