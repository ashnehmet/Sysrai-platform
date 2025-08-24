#!/bin/bash
# Digital Ocean Deployment Script for Sysrai Platform

echo "========================================="
echo "SYSRAI PLATFORM - DIGITAL OCEAN SETUP"
echo "========================================="

# Update system
apt-get update && apt-get upgrade -y

# Install Python 3.10
apt-get install -y python3.10 python3.10-venv python3-pip

# Install PostgreSQL
apt-get install -y postgresql postgresql-contrib

# Install Redis
apt-get install -y redis-server

# Install Nginx
apt-get install -y nginx certbot python3-certbot-nginx

# Create application directory
mkdir -p /var/www/sysrai
cd /var/www/sysrai

# Clone repository
git clone https://github.com/ashnehmet/Sysrai-platform.git .

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Setup PostgreSQL
sudo -u postgres psql <<EOF
CREATE DATABASE sysrai_db;
CREATE USER sysrai WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE sysrai_db TO sysrai;
EOF

# Create .env file
cat > .env <<EOF
DATABASE_URL=postgresql://sysrai:secure_password_here@localhost/sysrai_db
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=$(openssl rand -hex 32)
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_SKYREELS_ENDPOINT=https://your-pod-id.runpod.io
ENVIRONMENT=production
EOF

# Run database migrations
alembic upgrade head

# Configure Nginx
cat > /etc/nginx/sites-available/sysrai <<'NGINX'
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/sysrai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -s reload

# Create systemd service
cat > /etc/systemd/system/sysrai.service <<'SERVICE'
[Unit]
Description=Sysrai AI Film Platform
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/var/www/sysrai
Environment="PATH=/var/www/sysrai/venv/bin"
ExecStart=/var/www/sysrai/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE

# Start service
systemctl daemon-reload
systemctl enable sysrai
systemctl start sysrai

# Setup SSL (optional)
# certbot --nginx -d your-domain.com

echo ""
echo "========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================="
echo ""
echo "📊 Next Steps:"
echo "1. Update .env with your RunPod API key"
echo "2. Configure your domain in Nginx"
echo "3. Run: certbot --nginx -d your-domain.com"
echo "4. Access your platform at http://your-server-ip"
echo ""
echo "🎬 Your AI Film Platform is ready!"
echo "========================================="