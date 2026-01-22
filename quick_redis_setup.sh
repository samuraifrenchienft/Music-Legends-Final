# quick_redis_setup.sh
# Copy and paste these commands in WSL

echo "Setting up Redis without password requirements..."
echo

# Step 1: Allow sudo without password
echo "slim7600 ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/slim7600

echo "✅ Sudo password disabled"
echo

# Step 2: Update packages
echo "Updating packages..."
sudo apt update

echo "✅ Packages updated"
echo

# Step 3: Install Redis
echo "Installing Redis..."
sudo apt install redis-server -y

echo "✅ Redis installed"
echo

# Step 4: Start Redis
echo "Starting Redis..."
sudo service redis-server start

echo "✅ Redis started"
echo

# Step 5: Test Redis
echo "Testing Redis..."
redis-cli ping

echo
echo "🎉 Redis setup complete!"
echo "Your Windows bot can now connect to Redis on localhost:6379"
