#!/bin/bash
# Important: Use 'docker compose down && docker compose up -d' instead of 'restart'
# when you change .env variables!

cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                  ⚠️  IMPORTANT REMINDER ⚠️                       ║
╚══════════════════════════════════════════════════════════════════╝

🔄 WHEN UPDATING .ENV VARIABLES:

   ❌ DON'T USE: docker compose restart
      (This keeps old environment variables!)
   
   ✅ USE THIS INSTEAD:
      docker compose down
      docker compose up -d
   
   This recreates containers with new environment variables.

📝 QUICK COMMANDS:

   # Update .env and reload
   nano /root/spca-ai-assistant/.env
   docker compose down && docker compose up -d
   
   # Check if environment loaded correctly
   docker compose exec api printenv | grep API_KEY
   
   # View logs
   docker compose logs -f api
   
   # Test the chatbot
   curl http://localhost/health

🌐 CURRENT STATUS:
   Deployment: ✅ Complete
   API: http://devnook.xyz/
   Docs: http://devnook.xyz/docs
   
╔══════════════════════════════════════════════════════════════════╗
║  Everything is working! The chatbot is live! 🎉                 ║
╚══════════════════════════════════════════════════════════════════╝
EOF
