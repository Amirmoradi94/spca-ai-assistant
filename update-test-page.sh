#!/bin/bash
# Update the test chatbot page on devnook.xyz

echo "╔══════════════════════════════════════════════════════╗"
echo "║     Update Test Chatbot Page                         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

SOURCE="/root/spca-ai-assistant/test_chatbot.html"
DEST="/var/www/devnook.xyz/test.html"

if [ ! -f "$SOURCE" ]; then
    echo "❌ Source file not found: $SOURCE"
    exit 1
fi

echo "📋 Copying file..."
cp "$SOURCE" "$DEST"

if [ $? -eq 0 ]; then
    echo "✅ File copied successfully"
    echo ""
    echo "🌐 Test page updated at:"
    echo "   https://devnook.xyz/test"
    echo ""
    echo "📊 File details:"
    ls -lh "$DEST"
else
    echo "❌ Failed to copy file"
    exit 1
fi
