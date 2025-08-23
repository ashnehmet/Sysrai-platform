#!/bin/bash
# DigitalOcean Sysrai Platform Installation Script
# Save this as: deployment/digitalocean_install.sh
# Run with: bash digitalocean_install.sh

echo "================================================"
echo "SYSRAI PLATFORM - DIGITALOCEAN INSTALLATION"
echo "================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "Step 1: Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# Install core packages
echo "Step 2: Installing core packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx

# Install Python packages
echo "Step 3: Installing Python packages..."
pip3 install --upgrade pip
pip3 install \
    fastapi \
    uvicorn[standard] \
    sqlalchemy \
    psycopg2-binary \
    alembic \
    stripe \
    redis \
    celery[redis] \
    jwt \
    bcrypt \
    requests \
    aiohttp \
    python-multipart \
    jinja2 \
    python-dotenv

# Create application directory
echo "Step 4: Setting up application directory..."
mkdir -p /var/www/sysrai
cd /var/www/sysrai

# Clone repository (replace with actual repo)
echo "Step 5: Cloning Sysrai repository..."
# This will be replaced with actual GitHub repo URL
echo "# Repository will be cloned here" > placeholder.txt

# Setup PostgreSQL
echo "Step 6: Setting up PostgreSQL database..."
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE sysrai_platform;
CREATE USER sysrai WITH PASSWORD 'sysrai_secure_$(date +%s)';
GRANT ALL PRIVILEGES ON DATABASE sysrai_platform TO sysrai;
ALTER USER sysrai CREATEDB;
\q
EOF

# Get the generated password
DB_PASSWORD=$(sudo -u postgres psql -t -c "SELECT rolpassword FROM pg_authid WHERE rolname='sysrai';" | tr -d ' ')

# Setup Redis
echo "Step 7: Setting up Redis..."
systemctl start redis-server
systemctl enable redis-server

# Configure Redis
cat > /etc/redis/redis.conf << 'REDIS_EOF'
bind 127.0.0.1
port 6379
timeout 0
save 900 1
save 300 10
save 60 10000
maxmemory 256mb
maxmemory-policy allkeys-lru
REDIS_EOF

systemctl restart redis-server

# Create environment file
echo "Step 8: Creating environment configuration..."
cat > /var/www/sysrai/.env << ENV_EOF
# Database
DATABASE_URL=postgresql://sysrai:sysrai_secure_$(date +%s)@localhost/sysrai_platform

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)

# API Keys (to be filled in later)
STRIPE_SECRET_KEY=sk_test_REPLACE_WITH_YOUR_STRIPE_KEY
STRIPE_WEBHOOK_SECRET=whsec_REPLACE_WITH_YOUR_WEBHOOK_SECRET
RUNPOD_API_KEY=REPLACE_WITH_YOUR_RUNPOD_KEY
OPENAI_API_KEY=REPLACE_WITH_YOUR_OPENAI_KEY

# Platform settings
ENVIRONMENT=production
DEBUG=False
DOMAIN=localhost
ADMIN_EMAIL=admin@sysrai.com

# File storage
UPLOAD_DIR=/var/www/sysrai/uploads
MAX_UPLOAD_SIZE=100MB

# Costs and pricing
DEFAULT_CREDITS=10
CREDIT_PACKAGES={"small":50,"medium":150,"large":500,"mega":2000}
ENV_EOF

# Create uploads directory
mkdir -p /var/www/sysrai/uploads
mkdir -p /var/www/sysrai/static
mkdir -p /var/www/sysrai/templates
mkdir -p /var/www/sysrai/logs

# Setup Nginx
echo "Step 9: Configuring Nginx web server..."
cat > /etc/nginx/sites-available/sysrai << 'NGINX_EOF'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 100M;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Static files
    location /static {
        alias /var/www/sysrai/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # File uploads/downloads
    location /uploads {
        alias /var/www/sysrai/uploads;
        expires 1h;
    }
    
    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
NGINX_EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/sysrai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t
if [ $? -eq 0 ]; then
    systemctl restart nginx
    systemctl enable nginx
    echo "✅ Nginx configured successfully"
else
    echo "❌ Nginx configuration error"
    exit 1
fi

# Create systemd service for Sysrai
echo "Step 10: Creating Sysrai system service..."
cat > /etc/systemd/system/sysrai.service << 'SERVICE_EOF'
[Unit]
Description=Sysrai AI Movie Platform
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/var/www/sysrai
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/var/www/sysrai/.env
ExecStart=/usr/local/bin/uvicorn platform.monetization_platform:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Create Celery worker service
cat > /etc/systemd/system/sysrai-worker.service << 'WORKER_EOF'
[Unit]
Description=Sysrai Celery Worker
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/var/www/sysrai
EnvironmentFile=/var/www/sysrai/.env
ExecStart=/usr/local/bin/celery -A platform.tasks worker --loglevel=info --concurrency=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
WORKER_EOF

# Setup firewall
echo "Step 11: Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 8000  # Direct API access if needed

# Create log rotation
cat > /etc/logrotate.d/sysrai << 'LOGROTATE_EOF'
/var/www/sysrai/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 root root
    postrotate
        systemctl reload sysrai
    endscript
}
LOGROTATE_EOF

# Create monitoring script
cat > /var/www/sysrai/monitor.sh << 'MONITOR_EOF'
#!/bin/bash
# System monitoring script

echo "=== SYSRAI PLATFORM MONITORING ==="
echo "Date: $(date)"
echo ""

# Service status
echo "Services:"
systemctl is-active sysrai && echo "✅ Sysrai: Running" || echo "❌ Sysrai: Stopped"
systemctl is-active nginx && echo "✅ Nginx: Running" || echo "❌ Nginx: Stopped"
systemctl is-active postgresql && echo "✅ PostgreSQL: Running" || echo "❌ PostgreSQL: Stopped"
systemctl is-active redis && echo "✅ Redis: Running" || echo "❌ Redis: Stopped"

echo ""

# System resources
echo "System Resources:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')%"
echo "Memory: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
echo "Disk: $(df -h / | awk 'NR==2{print $5}')"

echo ""

# Application health
echo "Application Health:"
curl -s http://localhost/health > /dev/null && echo "✅ API: Responding" || echo "❌ API: Not responding"

# Database connectivity
sudo -u postgres psql -d sysrai_platform -c "SELECT 1;" > /dev/null 2>&1 && echo "✅ Database: Connected" || echo "❌ Database: Connection failed"

echo ""
echo "=== END MONITORING ==="
MONITOR_EOF

chmod +x /var/www/sysrai/monitor.sh

# Create deployment script for updates
cat > /var/www/sysrai/deploy.sh << 'DEPLOY_EOF'
#!/bin/bash
# Deployment script for updates

echo "Starting Sysrai deployment..."

# Pull latest code
git pull origin main

# Install/update dependencies
pip3 install -r requirements.txt

# Run database migrations (when available)
# python3 -m alembic upgrade head

# Restart services
systemctl restart sysrai
systemctl restart sysrai-worker

# Check health
sleep 5
curl -f http://localhost/health && echo "✅ Deployment successful" || echo "❌ Deployment failed"
DEPLOY_EOF

chmod +x /var/www/sysrai/deploy.sh

# Set correct permissions
chown -R root:root /var/www/sysrai
chmod -R 755 /var/www/sysrai
chmod 600 /var/www/sysrai/.env

# Enable services (but don't start yet - need the actual code first)
systemctl daemon-reload
systemctl enable sysrai
systemctl enable sysrai-worker

echo "================================================"
echo "✅ SYSRAI PLATFORM INSTALLATION COMPLETE!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Clone your repository to /var/www/sysrai"
echo "2. Update API keys in /var/www/sysrai/.env"
echo "3. Start services: systemctl start sysrai"
echo "4. Test: curl http://$(curl -s ifconfig.me)/health"
echo ""
echo "Useful commands:"
echo "  Monitor: /var/www/sysrai/monitor.sh"
echo "  Logs: journalctl -u sysrai -f"
echo "  Deploy: /var/www/sysrai/deploy.sh"
echo ""
echo "Your server IP: $(curl -s ifconfig.me)"
echo "Platform URL: http://$(curl -s ifconfig.me)"
echo "================================================"