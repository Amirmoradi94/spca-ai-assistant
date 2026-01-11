# SPCA AI Assistant - Deployment Summary
**Server:** 76.13.25.15 (devnook.xyz)  
**Date:** 2026-01-11  
**Status:** ✅ Successfully Deployed

---

## 🚀 Deployment Overview

The SPCA AI Assistant chatbot has been successfully deployed to **devnook.xyz** with the following architecture:

```
Internet → Nginx (Port 80/443) → FastAPI API (Port 8000) → PostgreSQL Database
                                   ↓
                            Docker Containers:
                            - spca-api (FastAPI)
                            - spca-db (PostgreSQL)
                            - spca-scraper (Background Jobs)
```

---

## ✅ What's Deployed

### 1. **API Services** (Running on Port 8000)
- FastAPI backend with RESTful endpoints
- Real-time chat session management
- Health monitoring endpoints
- Interactive API documentation

### 2. **Database** (PostgreSQL 16)
- PostgreSQL running in Docker container
- Automatic health checks enabled
- Persistent volume for data storage

### 3. **Background Services**
- Web scraper service for animal/content updates
- Scheduled job processor

### 4. **Web Server** (Nginx)
- Reverse proxy configuration
- Static file serving for widget
- CORS headers for cross-origin requests

### 5. **Embeddable Widget**
- JavaScript widget files served at `/widget/`
- Bilingual support (EN/FR)
- Responsive design with modern UI

---

## 🔗 Access Points

| Service | URL | Status |
|---------|-----|--------|
| **API Root** | http://devnook.xyz/ | ✅ Working |
| **Health Check** | http://devnook.xyz/health | ✅ Working |
| **API Documentation** | http://devnook.xyz/docs | ✅ Working |
| **Chat API** | http://devnook.xyz/api/v1/chat | ✅ Working |
| **Widget JS** | http://devnook.xyz/widget/src/index.js | ✅ Working |
| **Widget CSS** | http://devnook.xyz/widget/src/styles.css | ✅ Working |

---

## 📋 Important Files & Locations

### Project Directory
```bash
/root/spca-ai-assistant/
```

### Configuration Files
- **Environment Variables:** `/root/spca-ai-assistant/.env`
- **Docker Compose:** `/root/spca-ai-assistant/docker-compose.yml`
- **Nginx Config:** `/etc/nginx/sites-available/devnook.xyz`
- **App Config:** `/root/spca-ai-assistant/config/config.yaml`

### Data Directories
- **Logs:** `/root/spca-ai-assistant/logs/`
- **Content:** `/root/spca-ai-assistant/content/`
  - `content/animals/` - Animal profiles
  - `content/general/` - General SPCA content

---

## 🔑 Required: API Key Configuration

**⚠️ ACTION REQUIRED:** The application is deployed but you need to add your API keys to function properly.

### Edit the .env file:
```bash
cd /root/spca-ai-assistant
nano .env
```

### Add your API keys:
```bash
# Required for chatbot functionality
GOOGLE_API_KEY=your_actual_google_gemini_api_key_here

# Optional for enhanced scraping
ZYTE_API_KEY=your_actual_zyte_api_key_here
```

### Get API Keys:
1. **Google Gemini API Key** (Required)
   - Visit: https://aistudio.google.com/app/apikey
   - Create a new API key
   - Copy and paste into `.env`

2. **Zyte API Key** (Optional)
   - Visit: https://www.zyte.com/
   - Sign up for an account
   - Copy and paste into `.env`

### Restart after adding keys:
```bash
cd /root/spca-ai-assistant
docker compose restart
```

---

## 🛠️ Management Commands

### View Logs
```bash
# All services
cd /root/spca-ai-assistant && docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f scraper
docker compose logs -f db
```

### Restart Services
```bash
cd /root/spca-ai-assistant

# Restart all
docker compose restart

# Restart specific service
docker compose restart api
docker compose restart scraper
```

### Stop/Start Services
```bash
cd /root/spca-ai-assistant

# Stop all
docker compose down

# Start all
docker compose up -d

# Check status
docker compose ps
```

### Update Application
```bash
cd /root/spca-ai-assistant

# Pull latest changes
git pull

# Rebuild and restart
docker compose down
docker compose build
docker compose up -d
```

---

## 🔒 Security & SSL Setup

### Current Status
- ✅ HTTP (Port 80) - Working
- ⏳ HTTPS (Port 443) - Not yet configured

### Enable HTTPS with Let's Encrypt
```bash
# Install certbot
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate
certbot --nginx -d devnook.xyz -d www.devnook.xyz

# Certificates will auto-renew
# Nginx config will be automatically updated
```

---

## 📊 Testing the Chatbot

### 1. Test Health Endpoint
```bash
curl http://devnook.xyz/health
```

### 2. Create a Chat Session
```bash
curl -X POST "http://devnook.xyz/api/v1/chat/session?language=en"
```

### 3. Send a Chat Message
```bash
curl -X POST "http://devnook.xyz/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What dogs are available for adoption?",
    "session_id": "YOUR_SESSION_ID_HERE",
    "language": "en"
  }'
```

### 4. Embed Widget in Your Website
```html
<!-- Add before </body> tag -->
<script>
    window.SPCA_CHAT_CONFIG = {
        apiEndpoint: 'http://devnook.xyz/api/v1/chat',
        theme: { primaryColor: '#0066cc' },
        language: 'auto'
    };
</script>
<link rel="stylesheet" href="http://devnook.xyz/widget/src/styles.css">
<script src="http://devnook.xyz/widget/src/index.js" data-auto-init="true"></script>
```

---

## 🔧 Troubleshooting

### API Not Responding
```bash
# Check if containers are running
docker compose ps

# Check API logs
docker compose logs api

# Restart API
docker compose restart api
```

### Database Connection Issues
```bash
# Check database status
docker compose ps db

# View database logs
docker compose logs db

# Restart database
docker compose restart db
```

### Nginx Issues
```bash
# Test nginx config
nginx -t

# Restart nginx
systemctl restart nginx

# Check nginx logs
tail -f /var/log/nginx/devnook.xyz-error.log
```

### Widget Not Loading
```bash
# Verify files are accessible
curl -I http://devnook.xyz/widget/src/index.js

# Check if volume is mounted
docker compose exec api ls -la /app/widget/src/
```

---

## 📈 Monitoring & Maintenance

### Check System Health
```bash
# API health
curl http://devnook.xyz/health

# Container status
docker compose ps

# System resources
docker stats
```

### Database Backup
```bash
# Create backup
docker compose exec db pg_dump -U spca spca > backup_$(date +%Y%m%d).sql

# Restore backup
docker compose exec -T db psql -U spca spca < backup_20260111.sql
```

### Clean Up Old Docker Images
```bash
docker system prune -a
```

---

## 📝 API Endpoints Reference

### Chat Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Send message |
| POST | `/api/v1/chat/session` | Create session |
| GET | `/api/v1/chat/session/{id}` | Get session info |
| DELETE | `/api/v1/chat/session/{id}` | End session |

### Admin Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/scrape` | Trigger scrape job |
| POST | `/api/v1/admin/sync` | Sync to Google File Search |
| GET | `/api/v1/admin/stats` | Get system stats |

### Health Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | API info |

---

## 🎯 Next Steps

1. ✅ **CRITICAL:** Add your Google Gemini API key to `.env`
2. ✅ Restart services after adding API keys
3. 🔒 Set up SSL/HTTPS with Let's Encrypt
4. 🧪 Test the chatbot with real queries
5. 📊 Run initial scraping job to populate content
6. 🎨 Customize widget appearance and branding
7. 🔐 Add authentication for admin endpoints
8. 📧 Set up monitoring and alerts

---

## 🆘 Support

For issues or questions:
- Check logs: `docker compose logs -f`
- Review documentation: `/root/spca-ai-assistant/README.md`
- Test endpoints: http://devnook.xyz/docs

---

**Deployment completed successfully! 🎉**

*Remember to add your API keys to make the chatbot fully functional.*
