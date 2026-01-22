# wsl_no_password.sh
# Run this if you want to skip password setup

echo "Setting up WSL without password..."
echo

# Allow sudo without password
echo "slim7600 ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/slim7600

echo
echo "No password setup complete!"
echo "You can now use sudo without entering a password."
echo
echo "Test with:"
echo "sudo whoami"
echo
echo "Now install Redis:"
echo "sudo apt update"
echo "sudo apt install redis-server"
