# Luqi AI v18 — 72-Hour Launch Battle Plan
## Go Live Target: luqi-ai.com | Timeline: 0-72 hours from NOW

---

# HOUR 0-2: CRITICAL FIXES & LOCAL TEST

## Step 1: Apply These 3 Critical Fixes (I just made them)

Your local files now have these fixes applied. You MUST sync them to GitHub:

### Fix 1: requirements.txt — Added missing dependencies
Added: `stripe`, `sendgrid`, `pywebpush`, `gTTS`, `pyttsx3`, `python-multipart`, `numpy`

### Fix 2: start_server.py — Fixed app path
Changed `server:app` to `backend.router:app` (was crashing on startup)

### Fix 3: .env.example — Added all v18 environment variables
Added Stripe keys, SMTP settings, VAPID keys for push notifications

### Fix 4: Dockerfile — Updated to v18.0.0

## Step 2: Sync All Files to GitHub (DO THIS FIRST)

```bash
# Open PowerShell or Terminal
cd omega-super-ai

# 1. Create a GitHub Personal Access Token:
#    → Go to https://github.com/settings/tokens/new
#    → Token name: "Luqi AI Deploy"
#    → Expiration: 7 days (enough for launch)
#    → Select scope: [x] repo (FULL control of private repositories)
#    → Click "Generate token" and COPY it immediately

# 2. Run the sync script (pushes ALL files including large ones)
$env:GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
python3 push_to_github.py

# Expected output: "SUCCESS: Pushed 40+ files!"
```

If the script fails, manual alternative:
```bash
# Delete the broken files on GitHub first, then re-push
git pull origin main --rebase
git add -A
git commit -m "v18.0.0 launch — critical fixes + all modules"
git push origin main
```

## Step 3: Create Your .env File

```bash
copy .env.example .env
# Now EDIT .env with your real keys:
# - OPENAI_API_KEY (required)
# - STRIPE_SECRET_KEY (use test key: sk_test_...)
# - STRIPE_PUBLISHABLE_KEY (pk_test_...)
```

## Step 4: Local Test (MUST PASS before deploying)

```bash
cd omega-super-ai

# Install all dependencies (including the NEW ones)
pip install -r requirements.txt

# Start the server
python3 start_server.py

# You should see:
# "Luqi AI v18 Server is running!"
# "Local:    http://localhost:8000"
# "API Docs: http://localhost:8000/docs"
```

### Test Checklist (visit in browser):
- [ ] http://localhost:8000 → Frontend loads
- [ ] http://localhost:8000/docs → API docs load
- [ ] http://localhost:8000/api/health → Returns {"status": "healthy", "version": "18.0.0"}

If ANY of these fail, STOP and fix before continuing.

---

# HOUR 2-6: NAMECHEAP + CLOUDFLARE SETUP

## Namecheap Configuration (You already have the domain)

### Part A: Set Up Professional Email (YES — You need this)

**Option 1: Namecheap Private Email (Recommended — $15/year)**
1. Log in to https://namecheap.com
2. Go to **Domain List** → Click **Manage** next to `luqi-ai.com`
3. Click **Private Email** tab
4. Select **Starter** plan (1 mailbox, $14.88/year)
5. Create these mailboxes:
   - `support@luqi-ai.com` — Customer support
   - `billing@luqi-ai.com` — Payment/Stripe receipts
   - `admin@luqi-ai.com` — Your admin login
6. Complete checkout
7. Wait 15-30 minutes for MX records to propagate

**Option 2: Google Workspace ($6/month — More professional)**
1. Go to https://workspace.google.com
2. Sign up with `luqi-ai.com`
3. Create `support@luqi-ai.com`
4. Follow DNS verification steps

**Option 3: Zoho Mail (FREE — Good for starting)**
1. Go to https://www.zoho.com/mail/
2. Sign up for FREE plan
3. Add domain `luqi-ai.com`
4. Create `support@luqi-ai.com`
5. Follow DNS record instructions (add MX records in Namecheap)

> **My Recommendation: Start with Zoho Mail (free)**. You can upgrade later. Having `support@luqi-ai.com` makes you look professional to customers.

### Part B: Point Domain to Your Server (via Cloudflare)

**Why Cloudflare?** Free SSL (HTTPS), faster loading, DDoS protection — REQUIRED for Stripe.

```
Step 1: Add domain to Cloudflare
1. Go to https://dash.cloudflare.com/sign-up
2. Click "Add a Site"
3. Enter: luqi-ai.com
4. Select FREE plan
5. Cloudflare will scan your DNS records — click Continue

Step 2: Change Namecheap nameservers
1. In Namecheap: Domain List → Manage → Nameservers
2. Select "Custom DNS"
3. Enter Cloudflare's nameservers (they give you 2):
   Example:
   - lara.ns.cloudflare.com
   - greg.ns.cloudflare.com
   (Use the EXACT ones Cloudflare shows you)
4. Save changes

Step 3: Back in Cloudflare
1. Click "Done, check nameservers"
2. Wait 5-30 minutes for DNS propagation
3. Status changes to "Active" (green checkmark)

Step 4: Add DNS Records in Cloudflare
1. Go to DNS → Records
2. Add an A record:
   Type: A
   Name: @
   IPv4: YOUR_SERVER_IP (you get this after deploying)
   Proxy status: Proxied (orange cloud)
   TTL: Auto
3. Add a CNAME record:
   Type: CNAME
   Name: www
   Target: luqi-ai.com
   Proxy status: Proxied
   TTL: Auto

Step 5: Enable SSL (CRITICAL for Stripe)
1. Go to SSL/TLS
2. Set to "Full (Strict)"
3. Done! Cloudflare gives you free HTTPS.
```

### Part C: Namecheap Redirect (www → non-www)

1. In Namecheap: Domain List → Manage → Advanced DNS
2. Add URL Redirect Record:
   - Type: URL Redirect
   - Host: www
   - Value: https://luqi-ai.com
   - Unmasked

---

# HOUR 6-12: DEPLOY TO RAILWAY (Recommended)

## Why Railway? Fastest path to live. Zero config. Free tier.

```
Step 1: Deploy
1. Push ALL code to GitHub first (Hour 0-2)
2. Go to https://railway.app
3. Sign in with GitHub (same account as your repo)
4. Click "New Project"
5. Click "Deploy from GitHub repo"
6. Select: ttmodupe-hash / omega-super-ai
7. Railway auto-detects Dockerfile and deploys!

Step 2: Add Environment Variables
1. In Railway dashboard → Select your project
2. Click "Variables" tab
3. Add each variable from your .env file:
   OPENAI_API_KEY=sk-your-key
   STRIPE_SECRET_KEY=sk_test_your-key
   STRIPE_PUBLISHABLE_KEY=pk_test_your-key
   STRIPE_WEBHOOK_SECRET=whsec_your-secret
   SENDGRID_API_KEY=SG-your-key
   (Add ALL variables from .env)
4. Railway auto-redeploys when you add vars

Step 3: Get Your Server IP / URL
1. Click "Settings" tab
2. Click "Generate Domain" (or use the default one)
3. Your URL will be: https://omega-super-ai-production.up.railway.app
4. Copy this URL — you'll point your domain to it
```

### Alternative: Point Custom Domain on Railway
```
1. In Railway → Settings → Custom Domain
2. Click "Custom Domain"
3. Enter: luqi-ai.com
4. Railway gives you a CNAME target
5. In Cloudflare: Add CNAME record:
   Name: @
   Target: [Railway CNAME target]
   Proxy status: DNS only (gray cloud — NOT orange)
6. Back in Railway: Click "Check" to verify
7. Wait 5-15 minutes for SSL to provision
```

### Test Deployed Site:
```bash
curl https://luqi-ai.com/api/health
# Should return: {"status": "healthy", "version": "18.0.0", ...}
```

---

# HOUR 12-18: STRIPE SETUP

## Create Products & Prices (One-time setup)

```bash
# SSH into your server OR run locally with Stripe test key
python3 -c "
import asyncio
from backend.stripe_integration import setup_stripe_products
asyncio.run(setup_stripe_products())
"
```

This creates:
- **Luqi AI Free** — $0/month
- **Luqi AI Pro** — $19.99/month
- **Luqi AI Enterprise** — $29.99/month

## Verify in Stripe Dashboard

1. Go to https://dashboard.stripe.com/products
2. You should see 3 products
3. Click into each → verify prices are correct

## Set Up Stripe Webhook (After deploy)

```
1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. Endpoint URL: https://luqi-ai.com/api/stripe/webhook
4. Select events:
   [x] checkout.session.completed
   [x] invoice.payment_succeeded
   [x] invoice.payment_failed
   [x] customer.subscription.deleted
   [x] customer.subscription.updated
5. Click "Add endpoint"
6. Copy the Signing secret (starts with whsec_)
7. Add to Railway environment variables:
   STRIPE_WEBHOOK_SECRET=whsec_your-secret
```

## Test Payment Flow (Use Stripe test cards)

```
1. Open https://luqi-ai.com
2. Click "Subscription" in sidebar
3. Click "Upgrade to Pro"
4. In Stripe Checkout, use test card:
   Card number: 4242 4242 4242 4242
   Expiry: 12/30
   CVC: 123
   ZIP: 12345
5. Complete payment
6. Check Stripe dashboard → Payments → Should show "Succeeded"
```

---

# HOUR 18-24: FINAL TESTING

## Full Feature Test Checklist

### Core AI:
- [ ] Chat works (send message, get response)
- [ ] Streaming chat works
- [ ] File upload works (upload a PDF, ask questions)
- [ ] Image generation works
- [ ] Web search works
- [ ] Memory/conversation history works

### v14 SaaS:
- [ ] Subscription page loads
- [ ] Free tier works (100 messages/day)
- [ ] Pro checkout works (test card)
- [ ] Customer portal works (manage subscription)

### v15 ASI:
- [ ] Cognitive engine query works
- [ ] Education system explains a concept
- [ ] Voice system lists languages
- [ ] Physics simulator runs a simulation

### v16 Production:
- [ ] GitHub integration page loads
- [ ] Data export works
- [ ] Admin dashboard loads (/admin.html)

### v17 Captainship & Companionship:
- [ ] Captain project creation works
- [ ] Companion chat works

### v18 Automotive & Writing:
- [ ] Automotive diagnostic works
- [ ] Writing assistant grammar check works

### v13 Base:
- [ ] Financial analysis works
- [ ] Tax calculation works
- [ ] Multilingual support works

---

# HOUR 24-48: GO LIVE CHECKLIST

## Switch to Production Mode

```
1. In Stripe dashboard: Toggle "Test mode" OFF
2. Get LIVE keys from https://dashboard.stripe.com/apikeys
3. In Railway: Update environment variables:
   STRIPE_SECRET_KEY=sk_live_your-live-key
   STRIPE_PUBLISHABLE_KEY=pk_live_your-live-key
4. Add LIVE webhook endpoint:
   https://luqi-ai.com/api/stripe/webhook
5. Update webhook secret
```

## Security Checklist
- [ ] OPENAI_API_KEY is secure (not exposed in frontend)
- [ ] Stripe keys are server-side only
- [ ] .env file is in .gitignore
- [ ] No debug mode in production
- [ ] HTTPS is working (check lock icon in browser)

## Performance Checklist
- [ ] Page loads under 3 seconds
- [ ] API responds under 2 seconds
- [ ] Chat streaming works smoothly
- [ ] No console errors in browser dev tools

---

# HOUR 48-72: MARKETING & LAUNCH

## Go-Live Announcement

### Create These Accounts:
1. **Twitter/X**: @luqi_ai — Post launch announcement
2. **LinkedIn**: Create Luqi AI company page
3. **Product Hunt**: Submit at https://www.producthunt.com

### Launch Post Template:
```
🚀 Luqi AI is LIVE!

The AI platform built for Africa and the world.

✅ 85+ languages (including 54 African languages)
✅ AI Software Developer (25 languages, 20 frameworks)
✅ AI Automotive Diagnostic ("Check before you buy")
✅ AI Writing Assistant (grammar, style, readability)
✅ AI Project Captain (manage your projects)
✅ AI Companion (emotional support)
✅ K-PhD Education System
✅ Real-time voice in 92 languages

🆓 Free: 100 messages/day
⭐ Pro: $19.99/month — Unlimited
🏢 Enterprise: $29.99/month

Try it now: https://luqi-ai.com

#AI #Africa #Tech #Startup
```

### Communities to Share In:
- [ ] r/SideProject (Reddit)
- [ ] r/SaaS (Reddit)
- [ ] r/Africa (Reddit)
- [ ] Hacker News (Show HN)
- [ ] Indie Hackers
- [ ] Africa's Talking community
- [ ] Dev.to
- [ ] Hashnode

### Email Your First 10 Prospects:
Write personalized emails to:
- Friends who need AI tools
- Local businesses that could use automation
- Developers who need coding help
- Students who need tutoring
- Mechanics who want diagnostic AI

---

# TROUBLESHOOTING

## Problem: Server won't start
```bash
# Check Python version (must be 3.10+)
python3 --version

# Check all dependencies installed
pip install -r requirements.txt --force-reinstall

# Check .env file exists and has OPENAI_API_KEY
cat .env | grep OPENAI

# Try direct uvicorn
python3 -m uvicorn backend.router:app --host 0.0.0.0 --port 8000
```

## Problem: 500 errors on endpoints
```bash
# Check server logs
# In Railway: View logs in dashboard

# Common causes:
# 1. Missing import → pip install [missing-package]
# 2. Database not initialized → The modules auto-init on first call
# 3. OpenAI key invalid → Check key at platform.openai.com
```

## Problem: Stripe checkout not working
```
1. Check you're using TEST keys (sk_test_ not sk_live_)
2. Verify STRIPE_PUBLISHABLE_KEY is set correctly
3. Check browser console for JavaScript errors
4. Verify webhook endpoint URL is correct
```

## Problem: Domain not pointing to server
```
1. Check DNS propagation: https://dnschecker.org
2. Verify Cloudflare nameservers are set in Namecheap
3. Check A record points to correct IP
4. Wait up to 24 hours for full propagation
```

## Problem: HTTPS not working
```
1. In Cloudflare: SSL/TLS must be "Full (Strict)"
2. Verify orange cloud is ON (Proxied)
3. Check SSL certificate status in Cloudflare
```

---

# COST BREAKDOWN (First Month)

| Service | Cost | Why |
|---------|------|-----|
| Namecheap domain | $0 (already paid) | Annual renewals |
| Railway (Starter) | $5/month | Hosting |
| Cloudflare | $0 | Free SSL + CDN |
| Zoho Mail | $0 | Free plan |
| OpenAI API | ~$20-50/month | Pay per use |
| Stripe | 2.9% + 30c per transaction | Only on paid subscriptions |
| **Total** | **~$25-55/month** | Until you have paying customers |

When you get your first 10 Pro subscribers ($199.90/month revenue), you're profitable!

---

# YOUR NEXT 3 ACTIONS (Do These NOW)

1. **Run `push_to_github.py`** to sync all files with the critical fixes
2. **Sign up for Cloudflare** and add luqi-ai.com
3. **Sign up for Railway** and deploy from GitHub

Then follow the hour-by-hour plan above. You WILL be live within 72 hours.

---

# Summary of What I Fixed in This Session:

| File | Issue | Fix |
|------|-------|-----|
| requirements.txt | Missing 7 dependencies (stripe, sendgrid, etc.) | Added all v14-v18 deps |
| start_server.py | Used `server:app` instead of `backend.router:app` | Fixed app path |
| .env.example | Missing Stripe, email, notification vars | Complete v18 config |
| Dockerfile | Label said v13.0.0 | Updated to v18.0.0 |

**All fixes are in your local files. Push to GitHub to apply them.**
