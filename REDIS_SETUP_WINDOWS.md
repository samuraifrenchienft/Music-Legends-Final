# REDIS_SETUP_WINDOWS.md

## 🪟 Redis Setup for Windows - Complete Guide

### **🎯 Option 1: Microsoft Redis (Recommended)**

#### **Download and Install:**
1. Go to: https://github.com/microsoftarchive/redis/releases
2. Download: `redis-x64-3.0.504.msi` (or latest version)
3. Run the installer
4. ✅ **IMPORTANT**: Check "Add to PATH" during installation
5. Complete installation

#### **Test Installation:**
```bash
# Open NEW PowerShell window after installation
redis-server
# Should start Redis server

# In another PowerShell window
redis-cli ping
# Should return: PONG
```

### **🎯 Option 2: WSL2 (Linux Subsystem)**

#### **Install WSL2:**
```powershell
# In PowerShell (as Administrator)
wsl --install
```

#### **Install Redis in WSL:**
```bash
# In WSL terminal
sudo apt update
sudo apt install redis-server

# Start Redis
sudo service redis-server start

# Test Redis
redis-cli ping
```

### **🎯 Option 3: Docker (If you have Docker Desktop)**

#### **Install Docker Desktop:**
1. Download: https://www.docker.com/products/docker-desktop/
2. Install Docker Desktop
3. Restart computer

#### **Run Redis:**
```bash
# In PowerShell
docker run --name redis -p 6379:6379 -d redis:7-alpine

# Test Redis
docker exec redis redis-cli ping
```

### **🎯 Option 4: Chocolatey Package Manager**

#### **Install Chocolatey:**
```powershell
# In PowerShell (as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### **Install Redis:**
```bash
# In PowerShell
choco install redis-64
```

### **🧪 Test Your Installation:**
```bash
# Test Redis CLI
redis-cli ping

# Test Python connection
python test_redis_simple.py
```

### **🔧 Troubleshooting:**

#### **"redis-cli not found" after installation:**
1. Close all PowerShell windows
2. Open NEW PowerShell window
3. Try: `redis-cli ping`

#### **"Connection refused" error:**
1. Make sure Redis server is running: `redis-server`
2. Check if port 6379 is available
3. Try: `redis-cli -h localhost -p 6379 ping`

#### **"Permission denied" error:**
1. Run PowerShell as Administrator
2. Or use: `Start-Process redis-server -Verb RunAs`

### **📋 Quick Commands:**
```bash
# Start Redis server
redis-server

# Test connection
redis-cli ping

# Stop Redis server
redis-cli shutdown

# Check Redis version
redis-server --version
```

### **🎯 Recommendation:**
**Use Option 1 (Microsoft Redis)** - It's the most reliable for Windows!

### **🚀 After Installation:**
Once Redis is working, run:
```bash
python test_redis_simple.py
python main.py
```

Your bot will be fully functional with Redis! 🎮
