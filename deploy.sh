#!/bin/bash

# ================================================================
# SPCA AI Assistant - Deployment Script
# ================================================================
# This script deploys the application to devnook.xyz (76.13.25.15)
# ================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVER_IP="76.13.25.15"
SERVER_USER="root"
DEPLOY_DIR="/opt/spca-ai-assistant"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SPCA AI Assistant - Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if SSH connection works
echo "Testing SSH connection to $SERVER_IP..."
if ssh -o ConnectTimeout=5 "$SERVER_USER@$SERVER_IP" "echo 'Connection successful'" &>/dev/null; then
    print_status "SSH connection successful"
else
    print_error "Cannot connect to $SERVER_IP"
    echo "Please ensure:"
    echo "  1. Server is accessible"
    echo "  2. SSH keys are set up"
    echo "  3. Firewall allows SSH (port 22)"
    exit 1
fi

# Create deployment directory on server
echo ""
echo "Creating deployment directory on server..."
ssh "$SERVER_USER@$SERVER_IP" "mkdir -p $DEPLOY_DIR"
print_status "Deployment directory created: $DEPLOY_DIR"

# Copy project files to server
echo ""
echo "Copying project files to server..."
rsync -avz --exclude 'venv' \
           --exclude '__pycache__' \
           --exclude '*.pyc' \
           --exclude '.git' \
           --exclude '.env' \
           --exclude 'logs' \
           --exclude 'content/animals/*' \
           --exclude 'content/general/*' \
           "$PROJECT_DIR/" "$SERVER_USER@$SERVER_IP:$DEPLOY_DIR/"
print_status "Project files copied"

# Copy env template as .env
echo ""
echo "Setting up environment file..."
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && cp env.template .env"
print_status ".env file created from template"

# Install Docker if not present
echo ""
echo "Checking Docker installation..."
if ssh "$SERVER_USER@$SERVER_IP" "command -v docker &>/dev/null"; then
    print_status "Docker is already installed"
else
    print_warning "Docker not found. Installing Docker..."
    ssh "$SERVER_USER@$SERVER_IP" bash << 'EOF'
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl enable docker
        systemctl start docker
        rm get-docker.sh
EOF
    print_status "Docker installed"
fi

# Install Docker Compose if not present
echo ""
echo "Checking Docker Compose installation..."
if ssh "$SERVER_USER@$SERVER_IP" "command -v docker-compose &>/dev/null || docker compose version &>/dev/null"; then
    print_status "Docker Compose is already installed"
else
    print_warning "Docker Compose not found. Installing..."
    ssh "$SERVER_USER@$SERVER_IP" bash << 'EOF'
        DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d'"' -f4)
        curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
EOF
    print_status "Docker Compose installed"
fi

# Install Nginx if not present
echo ""
echo "Checking Nginx installation..."
if ssh "$SERVER_USER@$SERVER_IP" "command -v nginx &>/dev/null"; then
    print_status "Nginx is already installed"
else
    print_warning "Nginx not found. Installing..."
    ssh "$SERVER_USER@$SERVER_IP" "apt-get update && apt-get install -y nginx"
    print_status "Nginx installed"
fi

# Configure Nginx
echo ""
echo "Configuring Nginx..."
ssh "$SERVER_USER@$SERVER_IP" "cp $DEPLOY_DIR/nginx-devnook.xyz.conf /etc/nginx/sites-available/devnook.xyz"
ssh "$SERVER_USER@$SERVER_IP" "ln -sf /etc/nginx/sites-available/devnook.xyz /etc/nginx/sites-enabled/devnook.xyz"
ssh "$SERVER_USER@$SERVER_IP" "nginx -t && systemctl reload nginx" || print_warning "Nginx configuration test failed"
print_status "Nginx configured"

# Create necessary directories
echo ""
echo "Creating application directories..."
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && mkdir -p logs content/animals content/general"
print_status "Application directories created"

# Stop existing containers
echo ""
echo "Stopping existing containers (if any)..."
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && docker-compose down || true"
print_status "Existing containers stopped"

# Build and start containers
echo ""
echo "Building and starting Docker containers..."
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && docker-compose build"
print_status "Docker images built"

# Start services
echo ""
echo "Starting services..."
ssh "$SERVER_USER@$SERVER_IP" "cd $DEPLOY_DIR && docker-compose up -d"
print_status "Services started"

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."
if ssh "$SERVER_USER@$SERVER_IP" "curl -f http://localhost:8000/health &>/dev/null"; then
    print_status "API is healthy"
else
    print_warning "API health check failed. Check logs with: ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker-compose logs api'"
fi

# Display completion message
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. SSH to server: ssh $SERVER_USER@$SERVER_IP"
echo "2. Edit .env file: nano $DEPLOY_DIR/.env"
echo "3. Add your API keys:"
echo "   - GOOGLE_API_KEY (required)"
echo "   - ZYTE_API_KEY (optional)"
echo "4. Restart services: cd $DEPLOY_DIR && docker-compose restart"
echo ""
echo "Access points:"
echo "  - API: http://devnook.xyz/api/v1/"
echo "  - Docs: http://devnook.xyz/docs"
echo "  - Health: http://devnook.xyz/health"
echo ""
echo "View logs:"
echo "  ssh $SERVER_USER@$SERVER_IP 'cd $DEPLOY_DIR && docker-compose logs -f'"
echo ""
echo "For SSL/HTTPS, run certbot:"
echo "  ssh $SERVER_USER@$SERVER_IP 'certbot --nginx -d devnook.xyz -d www.devnook.xyz'"
echo ""
