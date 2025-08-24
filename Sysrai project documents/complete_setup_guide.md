# Complete Sysrai Setup Guide - Step by Step

## What You're Building

**Sysrai** = AI movie creation platform where users pay $250 to create films instead of $50M traditional costs.

**Architecture:**
- **Main Platform** (DigitalOcean): Users, payments, project management
- **SkyReels API** (RunPod): GPU-powered video generation (only runs when needed)
- **Cost Control**: GPU only charges when making videos = 95% savings

---

## Phase 1: GitHub Repository Setup (5 minutes)

### Step 1: Create Repository

1. **Go to github.com** and sign in
2. **Click green "New" button** (top left)
3. **Repository name**: `sysrai-platform`
4. **Description**: `AI Movie Creation Platform - $250 films instead of $50M`
5. **Check "Add a README file"**
6. **Click "Create repository"**

### Step 2: Upload Your Files

**Option A - GitHub Desktop (Easiest):**
1. **Download GitHub Desktop** from desktop.github.com
2. **Clone your new repository**
3. **Copy all your project files** into the cloned folder
4. **Commit and push**

**Option B - Command Line:**
```cmd
cd C:\your-project-folder
git init
git remote add origin https://github.com/YOURUSERNAME/sysrai-platform.git
git add .
git commit -m "Initial Sysrai platform upload"
git push -u origin main
```

### Step 3: Create Repository Structure

Create these folders in your repository:
```
sysrai-platform/
├── platform/              # Main platform code
├── skyreels-api/          # RunPod video generation
├── deployment/            # Setup scripts
├── testing/               # Automated tests
└── docs/                  # Documentation
```

---

## Phase 2: RunPod Setup - SkyReels API (15 minutes)

### Step 1: Create RunPod Account

1. **Go to runpod.io**
2. **Click "Sign Up"**
3. **Use GitHub login** (recommended)
4. **Add $50 credit** (enough for testing)

### Step 2: Create Template

1. **Go to "Templates" tab**
2. **Click "New Template"**
3. **Fill out:**
   - **Name**: `Sysrai-SkyReels-V2`
   - **Container Image**: `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel`
   - **Container Disk**: `50 GB`
   - **Volume Disk**: `100 GB`
   - **Volume Mount**: `/workspace`
   - **HTTP Ports**: `8000`
   - **TCP Ports**: `22`

4. **Start Script** (copy/paste):
```bash
#!/bin/bash
cd /workspace
git clone https://github.com/YOURUSERNAME/sysrai-platform.git
cd sysrai-platform/skyreels-api
pip install -r requirements.txt
python setup_skyreels.py
python skyreels_api_server.py
```

5. **Click "Save Template"**

### Step 3: Get API Key

1. **Go to Settings** (profile icon)
2. **Click "API Keys"**
3. **Create new key**: `Sysrai-Platform`
4. **Copy and save the key** (you'll need this)

### Step 4: Test Pod Creation

1. **Go to "Pods" tab**
2. **Click "Deploy"**
3. **Select your template**
4. **Choose GPU**: RTX 4090 ($0.44/hr)
5. **Click "Deploy"**
6. **Wait 3-5 minutes** for startup
7. **Click "Connect" -> "HTTP Service"**
8. **You should see**: SkyReels API running
9. **IMPORTANT**: Click "Terminate" when done testing

---

## Phase 3: DigitalOcean Setup - Main Platform (20 minutes)

### Step 1: Create DigitalOcean Account

1. **Go to digitalocean.com**
2. **Click "Sign up"**
3. **Use GitHub login**
4. **Verify email**
5. **Add payment method** (they give $200 free credit)

### Step 2: Create Droplet

1. **Click "Create" -> "Droplets"**
2. **Choose:**
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **Size**: $12/month (2GB RAM, 1 vCPU)
   - **Datacenter**: Closest to your location
   - **Authentication**: Password (easier for start)
3. **Hostname**: `sysrai-platform`
4. **Click "Create Droplet"**

### Step 3: Connect to Server

1. **Click on your droplet name**
2. **Click "Console" tab**
3. **Login as root** with your password

### Step 4: Install Platform

**Copy/paste these commands one by one:**

```bash
# Update system
apt update && apt upgrade -y

# Install requirements
apt install python3 python3-pip nodejs npm postgresql postgresql-contrib redis-server nginx git curl -y

# Install Python packages
pip3 install fastapi uvicorn sqlalchemy psycopg2-binary stripe redis celery playwright

# Create app directory
mkdir /var/www/sysrai
cd /var/www/sysrai

# Clone your repository (replace YOURUSERNAME)
git clone https://github.com/YOURUSERNAME/sysrai-platform.git .

# Install additional requirements
pip3 install -r requirements.txt
```

### Step 5: Setup Database

```bash
# Start services
systemctl start postgresql redis-server
systemctl enable postgresql redis-server

# Create database
sudo -u postgres psql << EOF
CREATE DATABASE sysrai_platform;
CREATE USER sysrai WITH PASSWORD 'sysrai_secure_pass_2024';
GRANT ALL PRIVILEGES ON DATABASE sysrai_platform TO sysrai;
\q
EOF
```

### Step 6: Configure Environment

```bash
# Create environment file
cat > /var/www/sysrai/.env << EOF
DATABASE_URL=postgresql://sysrai:sysrai_secure_pass_2024@localhost/sysrai_platform
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=sk_test_YOUR_STRIPE_KEY_HERE
RUNPOD_API_KEY=YOUR_RUNPOD_KEY_HERE
JWT_SECRET=sysrai_jwt_secret_$(date +%s)
ENVIRONMENT=production
EOF
```

### Step 7: Setup Web Server

```bash
# Create Nginx config
cat > /etc/nginx/sites-available/sysrai << 'EOF'
server {
    listen 80;
    server_name _;
    
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
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/sysrai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
```

### Step 8: Start Platform

```bash
# Create startup service
cat > /etc/systemd/system/sysrai.service << EOF
[Unit]
Description=Sysrai Platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/sysrai
EnvironmentFile=/var/www/sysrai/.env
ExecStart=/usr/local/bin/uvicorn platform.monetization_platform:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start platform
systemctl daemon-reload
systemctl enable sysrai
systemctl start sysrai
```

### Step 9: Test Setup

```bash
# Check if platform is running
systemctl status sysrai

# Test API endpoint
curl http://localhost/health

# Check logs if needed
journalctl -u sysrai -f
```

---

## Phase 4: Get Your IP Address and Test

### Find Your Platform URL

1. **In DigitalOcean console**: Look for "ipv4" address
2. **Or run this command**: `curl ifconfig.me`
3. **Your platform URL**: `http://YOUR-IP-ADDRESS`

### Test Your Platform

1. **Open browser** to `http://YOUR-IP-ADDRESS`
2. **You should see**: Sysrai platform homepage
3. **Test registration**: Create a user account
4. **Test dashboard**: Should load with 10 free credits

---

## Phase 5: Configure API Keys

### Get Stripe Keys

1. **Go to stripe.com** and create account
2. **Go to Developers -> API keys**
3. **Copy "Secret key"** (starts with `sk_test_`)
4. **Update your .env file**:

```bash
cd /var/www/sysrai
nano .env
# Replace YOUR_STRIPE_KEY_HERE with actual key
systemctl restart sysrai
```

### Configure RunPod Integration

1. **Edit platform configuration**:
```bash
nano /var/www/sysrai/platform/runpod_config.py
# Add your RunPod API key and template ID
```

2. **Test RunPod connection**:
```bash
python3 -c "
from platform.runpod_controller import RunPodController
controller = RunPodController('YOUR_RUNPOD_API_KEY')
print('RunPod connection test completed')
"
```

---

## Phase 6: Install Testing Framework

### Install Playwright Tests

```bash
cd /var/www/sysrai
pip3 install playwright pytest
playwright install chromium

# Run initial test
python3 testing/playwright_testing.py --url http://localhost
```

### Setup Continuous Testing

```bash
# Create testing service
cat > /etc/systemd/system/sysrai-testing.service << EOF
[Unit]
Description=Sysrai Continuous Testing
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/sysrai
ExecStart=/usr/bin/python3 testing/playwright_testing.py --continuous --url http://localhost
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable sysrai-testing
systemctl start sysrai-testing
```

---

## Phase 7: Create First Test Film

### Test Complete Workflow

1. **Open browser** to your platform
2. **Register new account**
3. **Click "Create Project"**
4. **Fill in details**:
   - Title: "Test Film"
   - Duration: 30 seconds
   - Source: "A story about a brave explorer"
5. **Click "Generate Script"** (should complete in 30 seconds)
6. **Click "Generate Storyboard"** (should complete in 1 minute)
7. **Click "Generate Video"** (this will start RunPod instance - takes 10-30 minutes)

### Monitor Progress

- **Platform logs**: `journalctl -u sysrai -f`
- **RunPod status**: Check RunPod dashboard
- **Cost tracking**: Monitor RunPod charges

---

## Phase 8: Domain Setup (Optional)

### Buy Domain

1. **Buy domain** (Namecheap, GoDaddy, etc.)
2. **Add A record** pointing to your DigitalOcean IP
3. **Wait for DNS propagation** (up to 24 hours)

### Setup SSL

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace YOUR-DOMAIN.com)
certbot --nginx -d YOUR-DOMAIN.com

# SSL auto-renewal is automatic
```

---

## Cost Summary

### Monthly Costs
- **DigitalOcean droplet**: $12/month
- **Domain** (optional): $1/month
- **Total fixed costs**: $13/month

### Variable Costs (Per Video)
- **30-second video**: ~$0.25 GPU cost
- **Customer pays**: $15-30
- **Profit per video**: $14.75-29.75 (95%+ margin)

### Break-Even
- **Need**: 1 customer/month to break even
- **10 customers/month**: ~$200 profit
- **50 customers/month**: ~$1,200 profit

---

## Troubleshooting

### Common Issues

**"Platform not loading"**
```bash
systemctl status sysrai
journalctl -u sysrai -f
```

**"Database connection error"**
```bash
systemctl status postgresql
sudo -u postgres psql -c "\l"
```

**"RunPod won't start"**
- Check RunPod credit balance
- Verify template configuration
- Check API key permissions

**"Video generation fails"**
- Check RunPod pod logs
- Verify SkyReels model downloaded
- Check GPU memory usage

### Getting Help

- **Check logs**: `journalctl -u sysrai -f`
- **Test health**: `curl http://localhost/health`
- **Database check**: `sudo -u postgres psql sysrai_platform`
- **Restart platform**: `systemctl restart sysrai`

---

## Next Steps

1. **Test everything works** with the guide above
2. **Configure Stripe** for real payments
3. **Add custom domain** for professional look
4. **Create marketing website** to attract customers
5. **Scale up** as you get more users

**You now have a complete AI movie platform that can generate films for $250 instead of $50M!**