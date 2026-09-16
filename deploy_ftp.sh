#!/bin/bash

# Exit on any error
set -e

echo "=============================================="
echo "  Live Wedding Gallery - FTP Server Setup     "
echo "=============================================="

# 1. Update and install dependencies
echo ">> Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git libgl1-mesa-glx libglib2.0-0

# 2. Clone the repository
echo ">> Cloning repository..."
cd /home/ubuntu
if [ -d "Live_Wedding_Gallery" ]; then
    echo "Directory exists, pulling latest..."
    cd Live_Wedding_Gallery
    git pull origin main
else
    git clone https://github.com/PashamDhanushReddy/Live_Wedding_Gallery.git
    cd Live_Wedding_Gallery
fi

# 3. Setup Python Virtual Environment
echo ">> Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Python requirements
echo ">> Installing Python dependencies..."
pip install -r backend/requirements.txt

# 5. Create the .env file template if it doesn't exist
if [ ! -f .env ]; then
    echo ">> Creating empty .env file..."
    cat <<EOF > .env
# Database
DATABASE_URL=your_neon_postgres_url_here

# Cloudinary
CLOUDINARY_1_CLOUD_NAME=your_cloud_name
CLOUDINARY_1_API_KEY=your_api_key
CLOUDINARY_1_API_SECRET=your_api_secret

# Other settings
DEBUG=False
EOF
fi

# 6. Setup Systemd Service
echo ">> Creating systemd background service..."
sudo tee /etc/systemd/system/wedding-ftp.service > /dev/null <<EOF
[Unit]
Description=Wedding FTP Server
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/Live_Wedding_Gallery
Environment="PATH=/home/ubuntu/Live_Wedding_Gallery/venv/bin"
ExecStart=/home/ubuntu/Live_Wedding_Gallery/venv/bin/python backend/ftp_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable wedding-ftp.service
sudo systemctl start wedding-ftp.service

echo "=============================================="
echo "  Setup Complete!                             "
echo "=============================================="
echo "IMPORTANT NEXT STEPS:"
echo "1. Run: nano /home/ubuntu/Live_Wedding_Gallery/.env"
echo "2. Paste your DATABASE_URL and Cloudinary keys into the file, then save (Ctrl+O, Enter, Ctrl+X)."
echo "3. Run: sudo systemctl restart wedding-ftp.service"
echo "4. Your FTP server is now running on Port 2121!"
