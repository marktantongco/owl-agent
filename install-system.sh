#!/bin/bash
# 🦉 OWL-AGENT System Setup Script
# Run with sudo: sudo ~/.owl-agent/install-system.sh

set -e

echo "🦉 OWL-AGENT System Setup"
echo "========================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo $0"
    exit 1
fi

echo ""
echo "📦 Installing packages..."

# Update package list
apt-get update -qq

# Install terminal emulators
echo "Installing terminal emulators..."
apt-get install -y -qq \
    foot \
    lxterminal \
    roxterm \
    tilix \
    terminology \
    extraterm \
    2>/dev/null || echo "Some terminal emulators may not be available"

# Install terminal multiplexers
echo "Installing terminal multiplexers..."
apt-get install -y -qq \
    tmux \
    screen \
    byobu \
    2>/dev/null || echo "Some multiplexers may not be available"

# Install Caffeine (screen keep-awake)
echo "Installing Caffeine..."
apt-get install -y -qq caffeine 2>/dev/null || echo "Caffeine may not be available"

# Install Go
echo "Installing Go..."
if ! command -v go &> /dev/null; then
    cd /tmp
    curl -fsSL https://go.dev/dl/go1.24.4.linux-amd64.tar.gz -o go.tar.gz
    tar -C /usr/local -xzf go.tar.gz
    echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile.d/go.sh
    echo 'export PATH=$PATH:/usr/local/go/bin' >> /root/.bashrc
    rm go.tar.gz
    echo "Go installed: $(/usr/local/go/bin/go version)"
else
    echo "Go already installed: $(go version)"
fi

# Enable Caffeine autostart
echo "Setting up Caffeine..."
mkdir -p /home/ubuntu/.config/autostart
cat > /home/ubuntu/.config/autostart/caffeine.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Caffeine
Exec=caffeine
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Disable the screensaver
EOF
chown -R ubuntu:ubuntu /home/ubuntu/.config/autostart

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Installed packages:"
echo "  - Terminal emulators: foot, lxterminal, roxterm, tilix, terminology, extraterm"
echo "  - Multiplexers: tmux, screen, byobu"
echo "  - Caffeine (screen keep-awake)"
echo "  - Go $(/usr/local/go/bin/go version 2>/dev/null || echo 'installed')"
echo ""
echo "🔄 Please run: source /home/ubuntu/.bashrc"
