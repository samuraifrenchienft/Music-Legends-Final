# wsl_password_setup.sh
# Run this in WSL to set up password

echo "Setting up WSL password..."
echo

# Set root password (no password for simplicity)
echo "Setting root password (press Enter twice for blank password):"
sudo passwd root

echo
echo "Now setting your user password:"
echo "Enter a new password (remember this for sudo):"
passwd

echo
echo "Password setup complete!"
echo "Use this password when prompted for sudo in WSL."
echo
echo "Test with:"
echo "sudo whoami"
