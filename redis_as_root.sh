# redis_as_root.sh
# Use root user to set up Redis

echo "Setting up Redis as root user..."
echo

# Switch to root
sudo su

# Now as root, install Redis
echo "Installing Redis..."
apt update
apt install redis-server -y

echo "Starting Redis..."
service redis-server start

echo "Testing Redis..."
redis-cli ping

echo "Exit root with: exit"
echo "Then test Redis as your user: redis-cli ping"
