#!/bin/bash

# Coolify Deployment Script for Hetzner
# This script helps configure your Coolify instance for Sysrai Platform

set -e

echo "🚀 Sysrai Platform - Coolify Deployment Helper"
echo "============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running on Hetzner server
echo "📍 Checking server environment..."
if [ -f /etc/hetzner-build ]; then
    print_success "Running on Hetzner server"
else
    print_warning "Not detected as Hetzner server, continuing anyway..."
fi

# Generate secure passwords and keys
echo ""
echo "🔐 Generating secure credentials..."
POSTGRES_PASSWORD=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 16)

# Create environment file for Coolify
echo ""
echo "📝 Creating .env.coolify file..."
cat > .env.coolify << EOF
# Generated Environment Variables for Coolify
# Copy these to your Coolify application settings

# Database
POSTGRES_DB=sysrai_db
POSTGRES_USER=sysrai
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis
REDIS_PASSWORD=$REDIS_PASSWORD

# JWT & Security
JWT_SECRET_KEY=$JWT_SECRET

# Application
ENVIRONMENT=production
DEBUG=false
PORT=8000

# Domain (update with your actual domain)
DOMAIN=your-domain.com

# API Keys (add these manually in Coolify)
# OPENAI_API_KEY=sk-your-openai-key
# RUNPOD_API_KEY=your-runpod-key
# RUNPOD_SKYREELS_ENDPOINT=https://your-pod.runpod.io
# RUNPOD_POD_ID=your-pod-id
# STRIPE_SECRET_KEY=sk_test_your-stripe-key
# STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
EOF

print_success "Environment file created: .env.coolify"

# Create Coolify configuration
echo ""
echo "📦 Creating Coolify configuration..."
cat > coolify.yaml << EOF
# Coolify Application Configuration
# Import this in your Coolify dashboard

name: sysrai-platform
type: docker-compose
source:
  type: github
  repository: https://github.com/ashnehmet/Sysrai-platform
  branch: main
  
build:
  type: docker-compose
  file: docker-compose.yml
  
environment:
  - PORT=8000
  - ENVIRONMENT=production
  
volumes:
  - postgres_data:/var/lib/postgresql/data
  - redis_data:/data
  - uploads:/app/uploads
  - videos:/app/videos
  - temp:/app/temp

networks:
  - sysrai_network

health_check:
  enabled: true
  path: /health
  interval: 30
  timeout: 10
  retries: 3

auto_deploy:
  enabled: true
  branch: main
EOF

print_success "Coolify configuration created: coolify.yaml"

# Create deployment instructions
echo ""
echo "📋 Creating deployment instructions..."
cat > COOLIFY_SETUP.md << EOF
# Coolify Setup Instructions

## 1. Install Coolify on Hetzner

\`\`\`bash
# SSH into your Hetzner server
ssh root@your-server-ip

# Install Coolify (one-line installer)
curl -fsSL https://get.coolify.io | bash
\`\`\`

## 2. Configure Coolify

1. Access Coolify at: http://your-server-ip:3000
2. Complete initial setup
3. Add your server as a destination

## 3. Deploy Sysrai Platform

1. Create new application in Coolify
2. Select "Docker Compose" as source
3. Connect GitHub repository: https://github.com/ashnehmet/Sysrai-platform
4. Use the generated environment variables from .env.coolify
5. Deploy!

## 4. Configure Domain & SSL

1. Add your domain in Coolify settings
2. Enable automatic SSL with Let's Encrypt
3. Configure DNS to point to your Hetzner server

## 5. Post-Deployment

1. Run database migrations:
   \`\`\`bash
   docker exec sysrai-web alembic upgrade head
   \`\`\`

2. Create admin user:
   \`\`\`bash
   docker exec -it sysrai-web python -c "
   from database import SessionLocal
   from models import User
   from auth import get_password_hash
   import secrets
   
   db = SessionLocal()
   admin = User(
       id=secrets.token_hex(16),
       email='admin@sysrai.ai',
       password_hash=get_password_hash('change_this_password'),
       credits=1000.0,
       subscription_tier='enterprise'
   )
   db.add(admin)
   db.commit()
   print('Admin created: admin@sysrai.ai')
   "
   \`\`\`

## 6. Connect RunPod

Add these to Coolify environment variables:
- RUNPOD_API_KEY
- RUNPOD_SKYREELS_ENDPOINT
- RUNPOD_POD_ID

## 7. Monitor

Check logs in Coolify dashboard or:
\`\`\`bash
docker logs sysrai-web -f
\`\`\`
EOF

print_success "Setup instructions created: COOLIFY_SETUP.md"

# Display next steps
echo ""
echo "=========================================="
echo "✨ Coolify deployment files prepared!"
echo "=========================================="
echo ""
echo "📌 Next Steps:"
echo "1. Review generated files:"
echo "   - .env.coolify (environment variables)"
echo "   - coolify.yaml (Coolify config)"
echo "   - COOLIFY_SETUP.md (setup guide)"
echo ""
echo "2. Commit and push to GitHub:"
echo "   git add ."
echo "   git commit -m 'Add Coolify deployment configuration'"
echo "   git push origin main"
echo ""
echo "3. Install Coolify on your Hetzner server:"
echo "   curl -fsSL https://get.coolify.io | bash"
echo ""
echo "4. Deploy via Coolify dashboard"
echo ""
print_warning "Remember to add your API keys in Coolify!"
echo ""
echo "🚀 Ready for deployment on Hetzner + Coolify!"