# install_redis_chocolatey.ps1
# Run this in PowerShell as Administrator

Write-Host "Installing Chocolatey..." -ForegroundColor Green

# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

Write-Host "Installing Redis..." -ForegroundColor Green

# Install Redis
choco install redis-64 -y

Write-Host "Testing Redis..." -ForegroundColor Green

# Test Redis
redis-cli ping

Write-Host "Redis installation complete!" -ForegroundColor Green
Write-Host "Start Redis server with: redis-server" -ForegroundColor Yellow
