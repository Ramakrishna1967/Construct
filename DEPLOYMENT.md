# Deployment Guide - Free Platforms

This guide covers deploying your AI Code Reviewer backend to free platforms that support Redis, Docker, and WebSockets.

---

## 🏆 Recommended: Render.com (BEST FREE OPTION)

**✅ Pros:**
- 750 hours/month free (enough for 1 service running 24/7)
- Native Redis support (free 25MB)
- Docker container support
- WebSocket support
- Auto-deploy from GitHub
- Free SSL certificates
- No credit card required

**❌ Limitations:**
- Services sleep after 15 min inactivity
- Cold start ~30 seconds

### Step-by-Step Deployment on Render

#### 1. Prepare Your Repository

Create `render.yaml` in your backend directory:

```yaml
services:
  # Web Service (Backend API)
  - type: web
    name: ai-code-reviewer
    env: docker
    dockerfilePath: ./Dockerfile
    plan: free
    region: oregon
    healthCheckPath: /health
    envVars:
      - key: GOOGLE_API_KEY
        sync: false  # You'll set this in dashboard
      - key: REDIS_URL
        fromDatabase:
          name: redis
          property: connectionString
      - key: LOG_LEVEL
        value: INFO
      - key: DOCKER_IMAGE
        value: python:3.11-slim
      - key: APP_PORT
        value: 8000

databases:
  # Redis Database
  - name: redis
    plan: free  # 25MB free
    ipAllowList: []  # Allow all
```

#### 2. Update Dockerfile

Make sure your `Dockerfile` exposes the correct port:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI (for sandbox)
RUN apt-get update && apt-get install -y \
    docker.io \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render uses PORT env variable
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

#### 3. Deploy on Render

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Create Render Account:**
   - Go to https://render.com
   - Sign up (free, no credit card)

3. **Create New Blueprint:**
   - Click "New +" → "Blueprint"
   - Connect your GitHub repo
   - Select the repo with your backend
   - Click "Apply"

4. **Set Environment Variables:**
   - Go to your service → "Environment"
   - Add `GOOGLE_API_KEY` (your Gemini API key)
   - Other vars are auto-set from `render.yaml`

5. **Deploy:**
   - Automatic deployment starts
   - Wait ~5-10 minutes for build
   - Get your URL: `https://ai-code-reviewer.onrender.com`

6. **Test:**
   ```bash
   curl https://your-app.onrender.com/health
   ```

**⚠️ Important Note:** Docker-in-Docker doesn't work on Render. You'll need to **disable the sandbox feature** or use alternative execution methods.

---

## 🚂 Alternative: Railway.app

**✅ Pros:**
- $5/month free credits
- Full Docker support
- Redis included
- WebSocket support
- Very fast deployments
- Better for Docker-in-Docker

**❌ Limitations:**
- Requires credit card verification
- Free tier has usage limits

### Deploy on Railway

#### 1. Create `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

#### 2. Deploy:

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login:**
   ```bash
   railway login
   ```

3. **Initialize Project:**
   ```bash
   cd backend
   railway init
   ```

4. **Add Redis:**
   ```bash
   railway add
   # Select "Redis"
   ```

5. **Set Environment Variables:**
   ```bash
   railway variables set GOOGLE_API_KEY="your_key_here"
   ```

6. **Deploy:**
   ```bash
   railway up
   ```

7. **Get URL:**
   ```bash
   railway domain
   ```

---

## 🪂 Alternative: Fly.io

**✅ Pros:**
- Generous free tier
- Full Docker support
- Redis via Upstash (free tier)
- WebSocket support
- Fast global edge network

**❌ Limitations:**
- Requires credit card
- More complex setup

### Deploy on Fly.io

#### 1. Install Fly CLI:

```bash
# Windows
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

# Mac/Linux
curl -L https://fly.io/install.sh | sh
```

#### 2. Login:

```bash
fly auth login
```

#### 3. Launch App:

```bash
cd backend
fly launch
# Choose: Yes to Dockerfile
# Choose: Region closest to you
# Choose: No to Postgres
# Choose: No to Redis (we'll add Upstash)
```

#### 4. Add Redis (Upstash):

```bash
fly redis create
# Note the connection URL
```

#### 5. Set Secrets:

```bash
fly secrets set GOOGLE_API_KEY="your_key_here"
fly secrets set REDIS_URL="your_redis_url_here"
```

#### 6. Deploy:

```bash
fly deploy
```

#### 7. Open App:

```bash
fly open
```

---

## 🔧 Modified Version for Vercel (Without Docker Sandbox)

If you MUST use Vercel, you'll need to remove the Docker sandbox dependency.

### Option A: Use External Code Execution API

Replace the Docker sandbox with a service like:
- **Judge0** (free tier): https://judge0.com
- **Piston** (open source): https://github.com/engineer-man/piston

### Option B: Disable Sandbox

Create a simplified version without code execution:

#### 1. Create `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ],
  "env": {
    "GOOGLE_API_KEY": "@google_api_key"
  }
}
```

#### 2. Modify Code:

Comment out Docker sandbox usage in `src/agent/nodes.py`:

```python
# Disable run_command for Vercel
elif action == "run_command":
    # result = run_command_sync(data["command"])
    result = "Command execution disabled on serverless platform"
```

#### 3. Use Vercel Redis:

```bash
vercel link
vercel env add REDIS_URL
```

#### 4. Deploy:

```bash
vercel --prod
```

**⚠️ Note:** WebSockets don't work on Vercel. You'd need to convert to HTTP polling or Server-Sent Events.

---

## 📊 Platform Comparison

| Platform | Free Tier | Redis | Docker | WebSockets | Credit Card | Best For |
|----------|-----------|-------|--------|------------|-------------|----------|
| **Render** | 750h/month | ✅ 25MB | ⚠️ Limited | ✅ | ❌ | **Recommended** |
| **Railway** | $5 credits | ✅ | ✅ | ✅ | ✅ | Docker-heavy |
| **Fly.io** | Generous | ✅ Via Upstash | ✅ | ✅ | ✅ | Global apps |
| **Vercel** | Unlimited | ⚠️ Paid | ❌ | ❌ | ❌ | Not suitable |
| **Heroku** | Limited | ⚠️ Paid | ⚠️ | ✅ | ✅ | Legacy option |

---

## 🎯 My Recommendation

**For your specific backend, I recommend:**

### 1st Choice: **Render.com**
- ✅ Completely free (no credit card)
- ✅ Easy setup with `render.yaml`
- ✅ Auto-deploy from GitHub
- ✅ Built-in Redis
- ⚠️ Disable Docker sandbox or use alternative

### 2nd Choice: **Railway.app**
- ✅ Better Docker support
- ✅ $5 free credits (lasts ~1 month)
- ✅ Very fast
- ❌ Requires credit card

---

## 🚀 Quick Start (Render - Recommended)

1. **Create GitHub repo and push code:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push
   ```

2. **Sign up on Render.com** (no credit card)

3. **Create New Web Service:**
   - Connect GitHub
   - Select repo
   - Environment: Docker
   - Add environment variable: `GOOGLE_API_KEY`

4. **Add Redis:**
   - Create new Redis instance
   - Copy connection URL
   - Add to web service as `REDIS_URL`

5. **Deploy and test:**
   ```bash
   curl https://your-app.onrender.com/health
   ```

Done! Your backend is live on a free platform! 🎉

---

## 🔧 Post-Deployment

### Disable Docker Sandbox (for Render)

Since Docker-in-Docker doesn't work on most free platforms, update `src/agent/nodes.py`:

```python
# In coder_node function
elif action == "run_command":
    # Option 1: Disable
    result = "Command execution not available. Code changes saved to files."
    
    # Option 2: Use Judge0 API instead
    # result = execute_via_judge0(data["command"])
```

### Monitor Your App

- **Render:** Dashboard → Logs
- **Railway:** Dashboard → Deployments → Logs
- **Fly.io:** `fly logs`

---

## 💰 Cost Optimization

All recommended platforms stay **FREE** if you:
- Use only 1 service
- Stay within resource limits
- Accept cold starts (Render)
- Don't exceed traffic limits

Need help with deployment? Let me know which platform you choose!
