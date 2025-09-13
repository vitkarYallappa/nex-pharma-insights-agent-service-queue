#!/bin/bash

# ============================================================================
# NEX Pharma Insights Agent Service - EC2 Deployment Script
# ============================================================================
# This script deploys the microservice to an EC2 instance with IAM role support

set -e  # Exit on any error

# Configuration
SERVICE_NAME="nex-pharma-insights"
SERVICE_USER="nex-pharma"
SERVICE_DIR="/opt/nex-pharma-insights"
VENV_DIR="$SERVICE_DIR/venv"
LOG_DIR="/var/log/nex-pharma-insights"
SYSTEMD_SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Update package list
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        supervisor \
        nginx \
        htop \
        unzip
    
    log_success "System dependencies installed"
}

# Create service user
create_service_user() {
    log_info "Creating service user: $SERVICE_USER"
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --shell /bin/false --home-dir "$SERVICE_DIR" --create-home "$SERVICE_USER"
        log_success "Service user created: $SERVICE_USER"
    else
        log_info "Service user already exists: $SERVICE_USER"
    fi
}

# Setup directories
setup_directories() {
    log_info "Setting up directories..."
    
    # Create service directory
    mkdir -p "$SERVICE_DIR"
    mkdir -p "$LOG_DIR"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$SERVICE_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    
    # Set permissions
    chmod 755 "$SERVICE_DIR"
    chmod 755 "$LOG_DIR"
    
    log_success "Directories created and configured"
}

# Deploy application code
deploy_application() {
    log_info "Deploying application code..."
    
    # Copy application files (assuming we're running from the project directory)
    cp -r . "$SERVICE_DIR/app"
    
    # Remove unnecessary files
    rm -rf "$SERVICE_DIR/app/.git" 2>/dev/null || true
    rm -rf "$SERVICE_DIR/app/__pycache__" 2>/dev/null || true
    rm -rf "$SERVICE_DIR/app/.pytest_cache" 2>/dev/null || true
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$SERVICE_DIR/app"
    
    log_success "Application code deployed"
}

# Setup Python virtual environment
setup_python_env() {
    log_info "Setting up Python virtual environment..."
    
    # Create virtual environment as service user
    sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"
    
    # Install requirements
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$SERVICE_DIR/app/requirements.txt"
    
    log_success "Python environment configured"
}

# Setup environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."
    
    # Copy production environment file
    cp "$SERVICE_DIR/app/deployment/production.env" "$SERVICE_DIR/.env"
    
    # Set ownership and permissions
    chown "$SERVICE_USER:$SERVICE_USER" "$SERVICE_DIR/.env"
    chmod 600 "$SERVICE_DIR/.env"  # Secure permissions for env file
    
    log_warning "Please update $SERVICE_DIR/.env with your actual API keys and configuration"
    
    log_success "Environment configuration setup complete"
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "$SYSTEMD_SERVICE_FILE" << EOF
[Unit]
Description=NEX Pharma Insights Agent Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$SERVICE_DIR/app
Environment=PATH=$VENV_DIR/bin
EnvironmentFile=$SERVICE_DIR/.env
ExecStart=$VENV_DIR/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $SERVICE_DIR

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service created and enabled"
}

# Setup database tables
setup_database() {
    log_info "Setting up database tables..."
    
    # Run database migrations as service user
    cd "$SERVICE_DIR/app"
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" scripts/migrate.py create-all
    
    log_success "Database tables created"
}

# Test IAM role access
test_iam_access() {
    log_info "Testing IAM role access..."
    
    # Test AWS CLI access (if available)
    if command -v aws &> /dev/null; then
        log_info "Testing AWS access with instance role..."
        aws sts get-caller-identity || log_warning "AWS CLI test failed - check IAM role permissions"
    else
        log_info "AWS CLI not available - will test with Python boto3"
    fi
    
    # Test with Python boto3
    cd "$SERVICE_DIR/app"
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "
import boto3
try:
    # Test DynamoDB access
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    response = dynamodb.list_tables()
    print('✅ DynamoDB access successful')
    
    # Test S3 access
    s3 = boto3.client('s3', region_name='us-east-1')
    response = s3.list_buckets()
    print('✅ S3 access successful')
    
    # Test Bedrock access
    bedrock = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    print('✅ Bedrock client created successfully')
    
except Exception as e:
    print(f'❌ AWS access test failed: {e}')
    print('Please check IAM role permissions')
"
    
    log_success "IAM access test completed"
}

# Start service
start_service() {
    log_info "Starting service..."
    
    systemctl start "$SERVICE_NAME"
    systemctl status "$SERVICE_NAME" --no-pager
    
    log_success "Service started successfully"
}

# Main deployment function
main() {
    log_info "Starting NEX Pharma Insights Agent Service deployment..."
    
    check_root
    install_dependencies
    create_service_user
    setup_directories
    deploy_application
    setup_python_env
    setup_environment
    create_systemd_service
    
    # Only setup database if not in test mode
    if [[ "${1:-}" != "--skip-db" ]]; then
        setup_database
    fi
    
    test_iam_access
    start_service
    
    log_success "Deployment completed successfully!"
    log_info "Service is running on port 8000"
    log_info "Check logs with: journalctl -u $SERVICE_NAME -f"
    log_info "Service status: systemctl status $SERVICE_NAME"
    
    echo ""
    log_warning "IMPORTANT: Update $SERVICE_DIR/.env with your actual API keys before production use"
}

# Run main function
main "$@" 