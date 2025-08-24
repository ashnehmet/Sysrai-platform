# DigitalOcean Setup Guide - Main Sysrai Platform

## Goal: Host main platform that manages users, payments, and calls RunPod API

## Step 1: Create DigitalOcean Account

1. **Go to digitalocean.com**
2. **Click "Sign up"**
3. **Use GitHub login** (recommended)
4. **Verify email address**
5. **Add payment method** (they give $200 credit for new accounts)

## Step 2: Create Droplet (Virtual Server)

1. **Click "Create" -> "Droplets"**
2. **Choose Configuration:**
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **CPU Options**: Regular with SSD
   - **Size**: $12/month (2 GB RAM, 1 vCPU, 50 GB SSD)
   - **Datacenter**: Choose closest to your users
   - **Authentication**: SSH keys (recommended) or password

3. **Add SSH Key** (if using):
   - **On Windows**: Use PuTTY to generate SSH key
   - **Copy public key** and paste in DigitalOcean
   - **Name**: "Sysrai-Platform-Key"

4. **Hostname**: `sysrai-platform`
5. **Click "Create Droplet"**

## Step 3: Connect to Your Server

### Option A: DigitalOcean Console (Easiest)
1. **Click on your droplet name**
2. **Click "Console" tab**
3. **You're now connected to your server**

### Option B: SSH from Windows
1. **Open Command Prompt**
2. **Connect**: `ssh root@your-droplet-ip`
3. **Enter password** when prompted

## Step 4: Install Platform Requirements

**Copy and paste these commands one by one:**

```bash
# Update system
apt update && apt upgrade -y

# Install Python and Node.js
apt install python3 python3-pip nodejs npm postgresql postgresql-contrib redis-server nginx git -y

# Install Python packages
pip3 install fastapi uvicorn sqlalchemy psycopg2-binary stripe redis celery

# Create app directory
mkdir /var/www/sysrai
cd /var/www/sysrai

# Clone your repository
git clone https://github.com/yourusername/sysrai-platform.git .
```

## Step 5: Setup Database

```bash
# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE sysrai_platform;
CREATE USER sysrai WITH PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE sysrai_platform TO sysrai;
\q
EOF
```

## Step 6: Configure Environment

```bash
# Create environment file
cat > /var/www/sysrai/.env << EOF
DATABASE_URL=postgresql://sysrai:secure_password_123@localhost/sysrai_platform
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=sk_test_your_stripe_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
RUNPOD_API_KEY=your_runpod_api_key_here
JWT_SECRET=your_jwt_secret_here
ENVIRONMENT=production
EOF
```

## Step 7: Setup Web Server (Nginx)

```bash
# Create Nginx configuration
cat > /etc/nginx/sites-available/sysrai << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
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
    }
    
    location /static {
        alias /var/www/sysrai/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/sysrai /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

## Step 8: Create Startup Script

```bash
# Create systemd service
cat > /etc/systemd/system/sysrai.service << EOF
[Unit]
Description=Sysrai Platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/sysrai
Environment=PATH=/usr/bin:/usr/local/bin
EnvironmentFile=/var/www/sysrai/.env
ExecStart=/usr/local/bin/uvicorn platform.monetization_platform:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable sysrai
systemctl start sysrai
```

## Step 9: Setup Domain (Optional)

1. **Buy domain** (Namecheap, GoDaddy, etc.)
2. **Add DNS A record** pointing to your droplet IP
3. **Wait for DNS propagation** (up to 24 hours)

## Step 10: Setup SSL Certificate (Free)

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

## Verification Steps

1. **Check if platform is running**: `systemctl status sysrai`
2. **Check logs**: `journalctl -u sysrai -f`
3. **Test API**: `curl http://your-ip/health`
4. **Test website**: Open browser to `http://your-ip`

## Cost Breakdown

- **Droplet**: $12/month (2GB RAM, 1 vCPU)
- **Database**: Included
- **SSL Certificate**: Free (Let's Encrypt)
- **Domain**: $10-15/year (optional)
- **Total**: ~$12/month

## Next Steps

1. **Test the complete setup**
2. **Configure Stripe payments**
3. **Setup RunPod auto-start/stop**
4. **Create user registration flow**