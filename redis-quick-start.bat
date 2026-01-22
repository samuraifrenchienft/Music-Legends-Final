# redis-quick-start.bat
@echo off
echo Starting Redis with Docker...
docker run --name music-legends-redis -p 6379:6379 -d redis:7-alpine
echo Redis started on port 6379
echo Testing connection...
timeout /t 3 >nul
docker exec music-legends-redis redis-cli ping
echo.
echo Redis is ready!
echo.
echo To stop Redis: docker stop music-legends-redis
echo To remove Redis: docker rm music-legends-redis
pause
