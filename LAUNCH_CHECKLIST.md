# Luqi AI v18.0.0 — Production Launch Checklist

## What's Built
- **70,354+ lines** of Python backend code
- **22 backend modules** across v13-v18
- **162+ API endpoints** (v14-v18 endpoint modules wired)
- **14 UI pages** (Dashboard, Chat, Developer, Website Builder, Knowledge Base, Habits, Virtual Labs, Captain, Companion, Subscription, System Status, Settings, Automotive, Writing)
- **PWA-ready** (service worker + manifest.json)
- **Real Stripe integration** (checkout, customer portal, webhooks)
- **Email system** (8 templates: welcome, receipts, reminders)
- **Auto-upgrading** capability analysis engine

## CRITICAL FIRST STEP: Push All Files to GitHub

Some large files (>100KB) cannot be pushed via the GitHub web UI. Use the provided script:

```bash
# 1. Go to your project folder
cd omega-super-ai

# 2. Create a GitHub Personal Access Token:
#    Visit: https://github.com/settings/tokens/new
#    Select scope: [x] repo (full control of private repositories)
#    Click "Generate token" and COPY it immediately

# 3. Run the push script
export GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
python3 push_to_github.py

# The script will push ALL files (including large ones like cognitive_engine.py)
# in a single commit using the Git Data API.
```

## BEFORE Taking Payments

### 1. Set Environment Variables
Create a `.env` file in your project root:
```bash
# Required for AI to work
OPENAI_API_KEY=sk-your-openai-key

# Required for payments
STRIPE_SECRET_KEY=sk_test_your-key        # Use test keys first
STRIPE_PUBLISHABLE_KEY=pk_test_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret

# Required for emails
SENDGRID_API_KEY=SG.your-sendgrid-key     # Optional - falls back to SMTP/mock

# Optional (enhances search)
SERPER_API_KEY=your-serper-key

# Optional (enhances web search fallback)
BROWSERLESS_API_KEY=your-key
```

### 2. Stripe Setup (One-Time)
```bash
# Install stripe
pip install stripe

# Option A: Use the automated setup (creates products in your Stripe dashboard)
python3 -c "
import asyncio
from backend.stripe_integration import setup_stripe_products
asyncio.run(setup_stripe_products())
"

# Option B: Manual setup in Stripe Dashboard
# 1. Go to https://dashboard.stripe.com/products
# 2. Create "Luqi AI Pro" - $19.99/month
# 3. Create "Luqi AI Enterprise" - $29.99/month
# 4. Copy the Price IDs into your .env:
#    STRIPE_PRICE_PRO=price_xxx
#    STRIPE_PRICE_ENTERPRISE=price_xxx
```

### 3. SSL/HTTPS (REQUIRED for Stripe & PWA)
**Option A: Cloudflare (Recommended - Free)**
1. Sign up at https://cloudflare.com
2. Add your domain `luqi-ai.com`
3. Change nameservers at Namecheap to Cloudflare's
4. Enable "Full (Strict)" SSL mode
5. Add A record pointing to your server IP

**Option B: Let's Encrypt**
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d luqi-ai.com -d www.luqi-ai.com
# Certificates saved to /etc/letsencrypt/live/luqi-ai.com/
```

### 4. Deploy to Production Server

**Option A: Railway.app (Easiest - Recommended)**
1. Push your code to GitHub (done via push_to_github.py above)
2. Go to https://railway.app, sign in with GitHub
3. Click "New Project" -> "Deploy from GitHub repo"
4. Select `omega-super-ai`
5. Add environment variables in Railway dashboard
6. Railway auto-detects the Dockerfile and deploys

**Option B: Render.com**
1. Go to https://render.com, sign in with GitHub
2. Click "New Web Service"
3. Select your repo
4. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.router:app --host 0.0.0.0 --port $PORT`
5. Add environment variables
6. Deploy (free tier available)

**Option C: DigitalOcean (Most Control)**
```bash
# Create a $6/month Droplet (Ubuntu 22.04)
# SSH into your droplet and run:

apt update && apt install -y python3-pip python3-venv nginx git

git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
cat > /etc/systemd/system/luqi.service << 'EOF'
[Unit]
Description=Luqi AI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/omega-super-ai
Environment=OPENAI_API_KEY=sk-your-key
Environment=STRIPE_SECRET_KEY=sk-your-key
ExecStart=/root/omega-super-ai/venv/bin/uvicorn backend.router:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl enable luqi
systemctl start luqi

# Set up Nginx reverse proxy
cat > /etc/nginx/sites-available/luqi << 'EOF'
server {
    listen 80;
    server_name luqi-ai.com www.luqi-ai.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

ln -s /etc/nginx/sites-available/luqi /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# Set up SSL with Certbot
certbot --nginx -d luqi-ai.com -d www.luqi-ai.com --agree-tos --non-interactive --email your-email@example.com
```

### 5. Domain Configuration (Namecheap)
1. Log in to https://namecheap.com
2. Go to Domain List -> Manage for `luqi-ai.com`
3. Under Nameservers, select "Custom DNS"
4. If using Cloudflare: Enter Cloudflare nameservers
5. If using DigitalOcean: Enter `ns1.digitalocean.com`, `ns2.digitalocean.com`
6. Save and wait 5-60 minutes for DNS propagation

### 6. Stripe Webhook Endpoint
After deploying:
1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. Endpoint URL: `https://luqi-ai.com/api/stripe/webhook`
4. Select events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
5. Copy the webhook signing secret
6. Add to your environment: `STRIPE_WEBHOOK_SECRET=whsec_...`

## LOCAL DEVELOPMENT (Test Before Deploying)

```bash
# 1. Clone and setup
git clone https://github.com/ttmodupe-hash/omega-super-ai.git
cd omega-super-ai
pip install -r requirements.txt
pip install stripe pywebpush

# 2. Set env vars (Windows PowerShell)
$env:OPENAI_API_KEY="sk-your-key"
$env:STRIPE_SECRET_KEY="sk-test-key"  # Use test keys!

# 3. Initialize databases
python3 -c "from backend.subscriptions import init_db; init_db()"
python3 -c "from backend.dashboard import init_db; init_db()"

# 4. Start server
python3 start_server.py
# OR: uvicorn backend.router:app --host 0.0.0.0 --port 8000 --reload

# 5. Test
# Open browser to http://localhost:8000
# API docs at http://localhost:8000/docs
# Health check: curl http://localhost:8000/api/health
```

## POST-LAUNCH MARKETING CHECKLIST

- [ ] Set up Google Analytics (free)
- [ ] Create Twitter/X account for Luqi AI
- [ ] Create LinkedIn page
- [ ] Write launch post for Product Hunt
- [ ] Post in relevant subreddits (r/SideProject, r/ SaaS)
- [ ] Share in African tech communities (Africa's Talking, Devcenter)
- [ ] Set up Sentry for error monitoring (free tier)
- [ ] Create tutorial videos (screen recordings)
- [ ] Set up Calendly for demo bookings
- [ ] Reach out to 10 potential customers personally

## SUBSCRIPTION TIERS

| Plan | Price | Features |
|------|-------|----------|
| Free | $0 | 100 messages/day, 5 projects, 1GB storage, basic support |
| Pro | $19.99/mo | Unlimited messages, 25 projects, 10GB, priority support, all AI models |
| Enterprise | $29.99/mo | Everything unlimited, 100GB, 24/7 support, custom AI, SSO, SLA |

## SUPPORT

If you get stuck:
1. Check the API docs at `/docs` when the server is running
2. Run self-test: `python3 self_test.py`
3. Run CLI: `python3 cli.py`
4. Check logs in the console where the server is running
