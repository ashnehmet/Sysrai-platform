# 🚀 Sysrai Platform - Coolify on Hetzner Deployment Guide

## Overview

Deploy the Sysrai AI Film Platform using Coolify on Hetzner Cloud for a cost-effective, self-hosted solution.

### Architecture Changes from Digital Ocean
- **Hosting**: Hetzner Cloud (better pricing, EU data centers)
- **Deployment**: Coolify (self-hosted PaaS, no vendor lock-in)
- **Storage**: Local volumes or Hetzner Object Storage (S3-compatible)
- **Containers**: Docker-based deployment for better portability

## 📋 Prerequisites

1. **Hetzner Cloud Account**
   - Create at: https://www.hetzner.com/cloud
   - Add credit (€20 minimum recommended)

2. **Hetzner Server**
   - CX21 or higher (2 vCPU, 4GB RAM, 40GB SSD)
   - Ubuntu 22.04 LTS
   - Cost: ~€5.83/month

3. **Domain Name** (optional but recommended)
   - For SSL and professional access

## 🛠️ Step 1: Server Setup

### 1.1 Create Hetzner Server

```bash
# Via Hetzner Cloud Console or CLI
hcloud server create \
  --name sysrai-platform \
  --type cx21 \
  --image ubuntu-22.04 \
  --datacenter fsn1-dc14
```

### 1.2 Initial Server Configuration

```bash
# SSH into your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install essential tools
apt install -y curl git wget ufw

# Configure firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 3000/tcp  # Coolify dashboard
ufw --force enable
```

## 🐳 Step 2: Install Coolify

### 2.1 One-Line Installation

```bash
# Install Coolify v4
curl -fsSL https://get.coolify.io | bash
```

This installs:
- Docker & Docker Compose
- Coolify dashboard
- Traefik reverse proxy
- PostgreSQL for Coolify

### 2.2 Access Coolify Dashboard

1. Open browser: `http://your-server-ip:3000`
2. Complete initial setup:
   - Create admin account
   - Set instance name
   - Configure email (optional)

## 📦 Step 3: Deploy Sysrai Platform

### 3.1 Add GitHub Repository

In Coolify Dashboard:

1. Go to **Projects** → **Create New Project**
2. Select **Add New Resource** → **Public Repository**
3. Enter repository: `https://github.com/ashnehmet/Sysrai-platform`
4. Branch: `main`

### 3.2 Configure Application

1. **Build Configuration**:
   - Build Pack: `Docker Compose`
   - Compose File: `docker-compose.yml`

2. **Environment Variables** (click "Environment Variables"):

```env
# Database
POSTGRES_DB=sysrai_db
POSTGRES_USER=sysrai
POSTGRES_PASSWORD=generate_secure_password_here

# Redis
REDIS_PASSWORD=generate_secure_password_here

# JWT & Security
JWT_SECRET_KEY=generate_with_openssl_rand_hex_32

# Application
ENVIRONMENT=production
DEBUG=false
PORT=8000

# API Keys (add your actual keys)
OPENAI_API_KEY=sk-your-openai-key
RUNPOD_API_KEY=your-runpod-key
RUNPOD_SKYREELS_ENDPOINT=https://your-pod.runpod.io
RUNPOD_POD_ID=your-pod-id

# Stripe (optional)
STRIPE_SECRET_KEY=sk_test_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret

# Domain
DOMAIN=your-domain.com
```

3. **Persistent Storage**:
   - Enable persistent volumes for:
     - `/app/uploads`
     - `/app/videos`
     - `/var/lib/postgresql/data`

### 3.3 Deploy Application

1. Click **Deploy**
2. Monitor build logs
3. Wait for health checks to pass

## 🔧 Step 4: Post-Deployment Configuration

### 4.1 Run Database Migrations

```bash
# SSH into server
ssh root@your-server-ip

# Access container
docker exec -it sysrai-web bash

# Run migrations
alembic upgrade head

# Exit container
exit
```

### 4.2 Create Admin User

```bash
docker exec -it sysrai-web python -c "
from database import SessionLocal
from models import User
from auth import get_password_hash
import secrets

db = SessionLocal()
admin = User(
    id=secrets.token_hex(16),
    email='admin@your-domain.com',
    password_hash=get_password_hash('secure_admin_password'),
    credits=1000.0,
    subscription_tier='enterprise'
)
db.add(admin)
db.commit()
print('Admin user created successfully!')
"
```

## 🌐 Step 5: Domain & SSL Setup

### 5.1 Configure DNS

Point your domain to Hetzner server:
```
A Record: @ → your-server-ip
A Record: www → your-server-ip
```

### 5.2 Enable SSL in Coolify

1. Go to application settings
2. Add domain: `your-domain.com`
3. Enable **Force HTTPS**
4. Enable **Auto-generate SSL**
5. Coolify uses Let's Encrypt automatically

## 🎬 Step 6: RunPod GPU Setup

### 6.1 Create RunPod Instance

1. Sign up at https://runpod.io
2. Create GPU Pod:
   - Template: PyTorch 2.1
   - GPU: RTX 4090
   - Expose ports: 8000

### 6.2 Deploy SkyReels on RunPod

```bash
# SSH into RunPod
ssh root@runpod-ip -p 22

# Setup SkyReels
wget https://raw.githubusercontent.com/ashnehmet/Sysrai-platform/main/setup_runpod.sh
chmod +x setup_runpod.sh
./setup_runpod.sh
```

### 6.3 Update Coolify Environment

Add RunPod endpoint to Coolify environment variables:
- `RUNPOD_SKYREELS_ENDPOINT=https://your-pod-id.runpod.io`

## 📊 Step 7: Monitoring & Maintenance

### 7.1 Health Monitoring

```bash
# Check application health
curl https://your-domain.com/health

# View logs in Coolify dashboard
# Or via SSH:
docker logs sysrai-web -f
```

### 7.2 Backup Strategy

```bash
# Backup database
docker exec sysrai-postgres pg_dump -U sysrai sysrai_db > backup_$(date +%Y%m%d).sql

# Backup uploaded files
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz /var/lib/docker/volumes/*_uploads
```

### 7.3 Updates

Coolify can auto-deploy from GitHub:
1. Enable **Auto Deploy** in settings
2. Push to main branch
3. Coolify rebuilds and deploys automatically

## 💰 Cost Comparison

### Hetzner + Coolify (NEW)
- **Hetzner CX21**: €5.83/month
- **RunPod GPU**: $0.44/hour (on-demand)
- **Total**: ~€6/month + GPU usage

### Digital Ocean (OLD)
- **Droplet**: $24/month
- **Spaces**: $5/month
- **RunPod GPU**: $0.44/hour
- **Total**: ~$29/month + GPU usage

**Savings**: ~75% on infrastructure costs!

## 🚨 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs sysrai-web
docker logs sysrai-postgres

# Restart containers
docker-compose restart
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
docker exec -it sysrai-postgres psql -U sysrai -d sysrai_db

# Check environment variables
docker exec sysrai-web env | grep DATABASE_URL
```

### Coolify Issues
```bash
# Restart Coolify
systemctl restart coolify

# Check Coolify logs
journalctl -u coolify -f
```

## 🎯 Production Checklist

- [ ] Server firewall configured
- [ ] SSL certificate active
- [ ] Database migrations complete
- [ ] Admin user created
- [ ] RunPod connected
- [ ] Health checks passing
- [ ] Backups configured
- [ ] Monitoring enabled
- [ ] API keys secured

## 📚 Additional Resources

- **Coolify Docs**: https://coolify.io/docs
- **Hetzner Cloud**: https://docs.hetzner.com/cloud
- **Docker Compose**: https://docs.docker.com/compose
- **RunPod Docs**: https://docs.runpod.io

---

## 🆘 Support

If you encounter issues:

1. Check Coolify dashboard logs
2. Review container logs: `docker logs [container-name]`
3. Verify environment variables are set correctly
4. Ensure all API keys are valid
5. Check network connectivity between services

The platform is now containerized and portable, making it easy to deploy on any Docker-compatible infrastructure!