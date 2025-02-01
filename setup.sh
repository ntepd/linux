#!/bin/bash

dependencies=(
    "python3-pip"
    "python3-venv"
    "postgresql"
    "postgresql-contrib"
    "nodejs"
    "npm"
)

echo "Checking and installing required system dependencies..."
for dep in "${dependencies[@]}"; do
    if ! dpkg -l | grep -q "^ii.*$dep"; then
        echo "Installing $dep..."
        sudo apt-get install -y "$dep"
    else
        echo "$dep is already installed"
    fi
done

CONFIG_DIR="$HOME/.config/ntepd"
ENV_FILE="$CONFIG_DIR/.env"

mkdir -p "$CONFIG_DIR"

if [ ! -f "$ENV_FILE" ]; then
    DB_PASSWORD=$(openssl rand -base64 32)
    
    echo "DATABASE_URL=postgresql://ntepddb:$DB_PASSWORD@localhost/ntepddb" > "$ENV_FILE"
    
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    sudo -u postgres psql -c "CREATE USER ntepddb WITH PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "CREATE DATABASE ntepddb OWNER ntepddb;"
fi