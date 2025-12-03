#!/bin/bash

# AI BOX Setup Script (Ubuntu/Debian)

echo "🚀 AI BOX Setup Started..."

# 1. Update System
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Docker
if ! command -v docker &> /dev/null
then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "✅ Docker already installed."
fi

# 3. Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# 4. Setup Firewall (UFW)
echo "🛡️ Configuring Firewall..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Dashboard
sudo ufw allow 5060/udp  # SIP
sudo ufw allow 10000/udp # RTP
sudo ufw --force enable

# 5. Create Service (Auto-start)
echo "⚙️ Creating Systemd Service..."
cat <<EOF | sudo tee /etc/systemd/system/bedel-ai.service
[Unit]
Description=Bedel AI Box Service
Requires=docker.service
After=docker.service

[Service]
Restart=always
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable bedel-ai
sudo systemctl start bedel-ai

echo "✅ Setup Complete! Your AI Box is ready."
