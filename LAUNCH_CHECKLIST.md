# Luqi AI — Production Launch Checklist

## Current Status
- 70,354 lines of Python backend code
- 22 backend modules
- 162+ API endpoints
- 14 UI pages (main app + admin)
- PWA-ready (service worker + manifest)

## CRITICAL: Do These Before Taking Payments

### 1. Stripe Real Integration (REQUIRED for payments)
```bash
# Install Stripe
py -3.11 -m pip install stripe

# Set your real Stripe keys
$env:STRIPE_SECRET_KEY="sk_live_..."
$env:STRIPE_PUBLISHABLE_KEY="pk_live_..."
$env:STRIPE_WEBHOOK_SECRET="whsec_..."

# Create products in Stripe Dashboard:
# 1. Go to https://dashboard.stripe.com/products
# 2. Create "Luqi AI Pro" - $19.99/month
# 3. Create "Luqi AI Enterprise" - $29.99/month
# 4. Copy price IDs into backend/subscriptions.py
```

### 2. OpenAI API Key (REQUIRED for AI to work)
```powershell
$env:OPENAI_API_KEY="sk-..."
```

### 3. SSL/HTTPS (REQUIRED for Stripe & PWA)
Options:
- **Cloudflare** (Free): Proxy through Cloudflare for instant HTTPS
- **Let's Encrypt** (Free): `certbot` on your server
- **Built-in**: Uvicorn supports SSL with cert files

### 4. Deploy to a Server (NOT localhost)
Options ranked by ease:
1. **Railway.app** — Easiest, auto-deploy from GitHub
2. **Render.com** — Free tier, GitHub integration
3. **DigitalOcean** — $6/mo, full control
4. **AWS EC2** — Most flexible

### 5. Domain DNS
- Point `luqi-ai.com` to your server IP
- Set up Cloudflare for SSL + caching

### 6. Email (for receipts, welcome, notifications)
Options:
- **SendGrid** (Free: 100/day)
- **Mailgun** (Free: 5,000/month)
- **AWS SES** (Cheapest at scale)

## LAUNCH SEQUENCE

```powershell
# Step 1: Pull latest code
git pull origin main

# Step 2: Install all dependencies
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install stripe pywebpush

# Step 3: Set environment variables
$env:OPENAI_API_KEY="sk-your-key"
$env:STRIPE_SECRET_KEY="sk-your-key"
$env:SENDGRID_API_KEY="SG.your-key"

# Step 4: Initialize databases
py -3.11 -c "from backend.subscriptions import init_db; init_db()"
py -3.11 -c "from backend.dashboard import init_db; init_db()"
py -3.11 -c "from backend.captainship import init_db; init_db()"
py -3.11 -c "from backend.companionship import init_db; init_db()"

# Step 5: Start server
py -3.11 start_server.py

# Step 6: Test health
curl http://localhost:8000/api/health

# Step 7: Deploy to cloud (see DEPLOY.md)
```

## POST-LAUNCH
- [ ] Set up Stripe webhook endpoint
- [ ] Configure SendGrid for transactional emails
- [ ] Set up Cloudflare for SSL
- [ ] Configure Google Analytics
- [ ] Set up error monitoring (Sentry)
- [ ] Create social media accounts
- [ ] Write launch announcement
