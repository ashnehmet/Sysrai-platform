# Sysrai - AI Film Generation Platform

Create full-length films with AI for $250 instead of $50 million. Sysrai uses cutting-edge AI technology to generate professional-quality videos from scripts, books, or ideas.

## 🎬 Features

- **Full-Length Films**: Generate movies from 1 minute to 3+ hours
- **AI Script Writing**: Automatic script generation from source material
- **Storyboarding**: Professional shot composition and camera angles
- **95% Cost Reduction**: $250 for a 60-minute film vs $50M traditional
- **Cloud GPU Processing**: Uses RunPod for efficient video generation

## 💰 Economics

| Duration | Customer Price | GPU Cost | Profit | Margin |
|----------|---------------|----------|--------|---------|
| 10 min | $40 | $0.73 | $39.27 | 98.2% |
| 30 min | $120 | $2.20 | $117.80 | 98.2% |
| 60 min | $240 | $4.40 | $235.60 | 98.2% |

## 🚀 Quick Start

### Prerequisites

- Digital Ocean account (or any VPS with Ubuntu 20.04+)
- RunPod account with API key
- Stripe account for payments
- Domain name (optional)

### Digital Ocean Deployment

1. **Create a Droplet**
   - Ubuntu 22.04
   - 2GB RAM minimum
   - $12/month plan recommended

2. **SSH into your server and run:**
```bash
wget https://raw.githubusercontent.com/ashnehmet/Sysrai-platform/main/deploy_digitalocean.sh
chmod +x deploy_digitalocean.sh
sudo ./deploy_digitalocean.sh
```

3. **Configure environment variables:**
```bash
sudo nano /var/www/sysrai/.env
# Add your RunPod API key and other credentials
```

4. **Restart the service:**
```bash
sudo systemctl restart sysrai
```

### RunPod Setup (One-Time)

1. **Create RunPod Account**
   - Sign up at [runpod.io](https://runpod.io)
   - Add $10-50 credit

2. **Create SkyReels Pod**
   - Template: PyTorch 2.1
   - GPU: RTX 4090 ($0.44/hr)
   - Save the pod ID and endpoint URL

3. **Install SkyReels on Pod**
```bash
# SSH into your RunPod instance
git clone https://github.com/SkyworkAI/SkyReels-V2.git
cd SkyReels-V2
pip install -r requirements.txt
python download_models.py
```

## 📁 Project Structure

```
sysrai-platform/
├── main.py              # FastAPI application
├── runpod_api.py        # RunPod GPU interface
├── database.py          # Database configuration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── crud.py              # Database operations
├── auth.py              # Authentication
├── pricing.py           # Pricing configuration
├── requirements.txt     # Python dependencies
├── deploy_digitalocean.sh  # Deployment script
└── .env.example         # Environment template
```

## 🔧 Development

### Local Setup

1. **Clone the repository:**
```bash
git clone https://github.com/ashnehmet/Sysrai-platform.git
cd Sysrai-platform
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Run the application:**
```bash
uvicorn main:app --reload
```

## 📊 API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/projects` - Create film project
- `GET /api/v1/projects/{id}` - Get project status
- `POST /api/v1/credits/purchase` - Buy credits

## 💳 Pricing Tiers

### Free Tier
- 10 credits on signup
- $5/minute video generation
- Max 10-minute videos

### Starter ($29.99/month)
- 100 credits included
- $3/minute video generation
- Max 60-minute videos

### Pro ($99.99/month)
- 500 credits included
- $2.50/minute video generation
- Max 180-minute videos

### Enterprise ($499.99/month)
- 3000 credits included
- $2/minute video generation
- Unlimited video length
- Priority support

## 🛠️ Technology Stack

- **Backend**: FastAPI, SQLAlchemy, Celery
- **Database**: PostgreSQL, Redis
- **AI Models**: SkyReels V2 (via RunPod)
- **Payments**: Stripe
- **Storage**: Digital Ocean Spaces
- **Deployment**: Digital Ocean, Nginx

## 📈 Monitoring

Monitor your platform:
- Application logs: `sudo journalctl -u sysrai -f`
- Nginx logs: `sudo tail -f /var/log/nginx/access.log`
- Database: `sudo -u postgres psql sysrai_db`

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is proprietary software. See [LICENSE](LICENSE) for details.

## 🆘 Support

- Documentation: [docs.sysrai.ai](https://docs.sysrai.ai)
- Email: support@sysrai.ai
- Discord: [Join our community](https://discord.gg/sysrai)

## 🚀 Roadmap

- [ ] Frontend React application
- [ ] Mobile app
- [ ] Voice cloning integration
- [ ] Multi-language support
- [ ] Real-time collaboration
- [ ] Custom actor models

---

**Ready to revolutionize filmmaking?** Start generating AI films today at a fraction of traditional costs!