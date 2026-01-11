#!/bin/bash
# Quick Commands Reference for SPCA AI Assistant

cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║        SPCA AI Assistant - Quick Commands Reference          ║
║                    devnook.xyz (76.13.25.15)                 ║
╚══════════════════════════════════════════════════════════════╝

📍 PROJECT DIRECTORY
   cd /root/spca-ai-assistant

🔧 CONFIGURATION
   nano .env                          # Edit environment variables
   nano config/config.yaml            # Edit app configuration

🐳 DOCKER COMMANDS
   docker compose ps                  # Check status
   docker compose up -d               # Start all services
   docker compose down                # Stop all services
   docker compose restart             # Restart all services
   docker compose restart api         # Restart specific service
   docker compose logs -f             # View all logs
   docker compose logs -f api         # View API logs
   docker compose build               # Rebuild images

🌐 NGINX COMMANDS
   nginx -t                           # Test config
   systemctl restart nginx            # Restart nginx
   systemctl status nginx             # Check status
   tail -f /var/log/nginx/devnook.xyz-error.log  # View errors

🔍 TESTING
   curl http://devnook.xyz/health     # Health check
   curl http://devnook.xyz/           # API info
   curl http://devnook.xyz/docs       # API docs

🔑 ADD API KEYS (REQUIRED!)
   1. Edit .env file:
      nano /root/spca-ai-assistant/.env
   
   2. Add your keys:
      GOOGLE_API_KEY=your_key_here
      ZYTE_API_KEY=your_key_here
   
   3. Restart:
      docker compose restart

🔒 ENABLE HTTPS
   certbot --nginx -d devnook.xyz -d www.devnook.xyz

💾 DATABASE BACKUP
   docker compose exec db pg_dump -U spca spca > backup.sql

📊 MONITOR RESOURCES
   docker stats                       # Resource usage
   df -h                              # Disk space
   free -h                            # Memory usage

🆘 TROUBLESHOOTING
   docker compose logs api --tail=50  # Last 50 API logs
   docker compose ps                  # Service status
   systemctl status nginx             # Nginx status

📚 DOCUMENTATION
   cat /root/spca-ai-assistant/DEPLOYMENT_SUMMARY.md
   cat /root/spca-ai-assistant/README.md

🌍 ACCESS POINTS
   API:    http://devnook.xyz/
   Docs:   http://devnook.xyz/docs
   Health: http://devnook.xyz/health
   Widget: http://devnook.xyz/widget/src/index.js

╔══════════════════════════════════════════════════════════════╗
║  Next Step: Add your API keys to .env and restart services! ║
╚══════════════════════════════════════════════════════════════╝
EOF
