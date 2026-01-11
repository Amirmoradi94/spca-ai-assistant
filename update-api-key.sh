#!/bin/bash
# Script to update Google API Key

echo "╔════════════════════════════════════════════════════╗"
echo "║     Update Google Gemini API Key                  ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

read -p "Enter your new Google API Key: " NEW_API_KEY

if [ -z "$NEW_API_KEY" ]; then
    echo "❌ No API key provided. Exiting."
    exit 1
fi

echo ""
echo "Updating .env file..."
sed -i "s|GOOGLE_API_KEY=.*|GOOGLE_API_KEY=$NEW_API_KEY|" /root/spca-ai-assistant/.env

if [ $? -eq 0 ]; then
    echo "✅ API key updated in .env"
else
    echo "❌ Failed to update .env file"
    exit 1
fi

echo ""
echo "Restarting services..."
cd /root/spca-ai-assistant && docker compose restart

echo ""
echo "✅ Services restarted!"
echo ""
echo "Testing API key..."
sleep 5

# Create session and test
SESSION_ID=$(curl -s -X POST "http://localhost/api/v1/chat/session?language=en" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)

echo "Sending test message..."
RESPONSE=$(curl -s -X POST "http://localhost/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Hi\", \"session_id\": \"$SESSION_ID\", \"language\": \"en\"}" 2>&1)

# Check logs for errors
if docker compose logs api --tail=10 | grep -q "API key not valid"; then
    echo ""
    echo "❌ API key is still invalid. Please check:"
    echo "   1. The key is correct"
    echo "   2. Generative Language API is enabled"
    echo "   3. Try generating a new key at:"
    echo "      https://aistudio.google.com/app/apikey"
else
    echo ""
    echo "✅ API key appears to be working!"
fi

echo ""
echo "View logs: docker compose logs -f api"
