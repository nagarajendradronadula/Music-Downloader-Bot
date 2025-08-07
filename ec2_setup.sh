#!/bin/bash

# EC2 Setup Script for Music Bot
echo "🖥️ Setting up Music Bot on EC2..."

# Update system
sudo yum update -y

# Install Python 3.9
sudo yum install python3 python3-pip -y

# Install FFmpeg
sudo yum install -y epel-release
sudo yum install -y ffmpeg

# Create bot directory
mkdir -p /home/ec2-user/music-bot
cd /home/ec2-user/music-bot

# Copy bot files (you'll upload these)
# direct_bot.py and requirements.txt should be uploaded

# Install Python dependencies
pip3 install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/music-bot.service > /dev/null <<EOF
[Unit]
Description=Music Downloader Telegram Bot
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/music-bot
ExecStart=/usr/bin/python3 direct_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable music-bot
sudo systemctl start music-bot

echo "✅ Music bot service started!"
echo "📊 Check status: sudo systemctl status music-bot"
echo "📝 View logs: sudo journalctl -u music-bot -f"