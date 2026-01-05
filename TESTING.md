# Testing the SPCA AI Assistant

## Quick Start with Test UI

### 1. Start the Services

```bash
# Make sure you have .env configured
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Start Docker services
docker-compose up -d --build

# Wait for services to be ready (~10 seconds)
```

### 2. Open the Test Interface

Simply open the testing UI in your browser:

```bash
# macOS
open test_chatbot.html

# Linux
xdg-open test_chatbot.html

# Windows
start test_chatbot.html

# Or drag the file into your browser
```

The test UI will automatically connect to `http://localhost:8000/api/v1/chat`

### 3. Test the Chatbot

#### Step 1: Create a Session
- The UI automatically creates a session on load
- Or click "🔄 New Session" button in the left sidebar
- You should see: "✅ New session created successfully!"

#### Step 2: Send Test Messages

**Quick Test Buttons** (in sidebar):
- 🐕 Dogs - "What dogs are available for adoption?"
- 🐱 Cats - "What cats are available for adoption?"
- 💰 Fees - "What are the adoption fees?"
- 🕒 Hours - "What are your opening hours?"

**Or type your own message**:
1. Type in the text area at the bottom
2. Press Enter or click "Send"
3. Watch the chatbot response appear

#### Step 3: Review Response Details

The UI shows:
- **Message content**: The chatbot's response
- **Sources** (if available): Which documents the answer came from
- **Suggested questions**: Follow-up questions you can click

---

## Testing Checklist

### ✅ Before Testing

- [ ] Docker services are running (`docker-compose ps`)
- [ ] API is accessible (`curl http://localhost:8000/health`)
- [ ] Database has tables (`docker-compose exec db psql -U spca -d spca -c "\dt"`)
- [ ] Google API key is set in `.env`

### ✅ Basic Functionality Tests

- [ ] Session creates successfully (see Session ID in sidebar)
- [ ] Can send a message
- [ ] Receives a response from chatbot
- [ ] Can click suggested questions
- [ ] Can switch between EN/FR languages
- [ ] Status shows "Connected" (green dot)

### ✅ Feature Tests

- [ ] **Session Management**
  - Create new session
  - Send multiple messages (conversation context)
  - End session
  - Create another session

- [ ] **Language Switching**
  - Switch to French (fr)
  - Create new session
  - Send message in French
  - Verify response is in French

- [ ] **Error Handling**
  - Stop API (`docker-compose stop api`)
  - Try sending message
  - Should see error message
  - Restart API (`docker-compose start api`)

- [ ] **Message History**
  - Send multiple messages
  - Verify chatbot remembers context
  - Example:
    1. "Do you have dogs?"
    2. "What about the brown one?" ← should understand context

### ✅ Data Flow Tests

1. **Scrape Animals**
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/scrape \
     -H "Content-Type: application/json" \
     -d '{"job_type": "animals"}'
   ```

2. **Sync to Google**
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/sync \
     -H "Content-Type: application/json" \
     -d '{"sync_type": "animals"}'
   ```

3. **Refresh Files in Chatbot**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/refresh-files
   ```

4. **Test in UI**
   - Ask: "What dogs are available?"
   - Should get real data from scraped animals

---

## Test UI Features

### Left Sidebar

#### Session Info
- **Session ID**: Current session identifier
- **Messages**: Number of messages in conversation
- **Language**: Current language (en/fr)

#### Controls
- **API Endpoint**: Change API URL (default: `http://localhost:8000/api/v1/chat`)
- **Language**: Switch between English/French
- **New Session**: Create a fresh session
- **Clear Messages**: Clear chat display (keeps session)
- **End Session**: Terminate current session

#### Quick Test Queries
Pre-configured test questions for quick testing

#### Log Console
Real-time logs showing:
- Session creation
- Message sending/receiving
- Errors
- API responses

### Main Chat Area

#### Header
- Connection status indicator (green = connected)
- Real-time status updates

#### Message Display
- **User messages**: Blue background
- **Assistant messages**: White background
- **System messages**: For notifications
- **Error messages**: Red background
- **Typing indicator**: Animated dots while waiting

#### Input Area
- Multi-line text input
- Auto-resize (up to 150px)
- Press Enter to send (Shift+Enter for new line)

---

## Testing Scenarios

### Scenario 1: First-Time Setup

```
1. Start services: docker-compose up -d
2. Open test_chatbot.html
3. See "New session created successfully"
4. Click "🐕 Dogs"
5. Should see: "I don't have specific information about available dogs..."
   (Because no data is scraped yet)
6. Run scrape: curl -X POST http://localhost:8000/api/v1/admin/scrape ...
7. Run sync: curl -X POST http://localhost:8000/api/v1/admin/sync ...
8. Refresh files: curl -X POST http://localhost:8000/api/v1/chat/refresh-files
9. Click "🔄 New Session" (to get updated file list)
10. Click "🐕 Dogs" again
11. Should now see: "We have several dogs available: Logan, Max, ..."
```

### Scenario 2: Conversation Context

```
1. Send: "Do you have any dogs?"
   Response: "Yes! We have Logan, Max, Buddy..."

2. Send: "Tell me more about Logan"
   Response: "Logan is a 5-year-old mixed breed..."
   (Chatbot remembers Logan from previous message)

3. Send: "What about cats?"
   Response: "We have several cats available..."

4. Send: "What was the name of the dog you mentioned earlier?"
   Response: "I mentioned Logan, Max, and Buddy..."
   (Chatbot remembers conversation history)
```

### Scenario 3: Bilingual Testing

```
1. Change Language to "French" in sidebar
2. Click "🔄 New Session"
3. Type: "Avez-vous des chiens disponibles?"
4. Response should be in French: "Oui! Nous avons plusieurs chiens..."
5. Continue conversation in French
6. Switch back to English
7. Create new session
8. Conversation now in English
```

### Scenario 4: Error Recovery

```
1. Send a message successfully
2. Stop API: docker-compose stop api
3. Try sending another message
4. Should see error: "Failed to send message: Failed to fetch"
5. Status changes to "Disconnected" (red dot)
6. Restart API: docker-compose start api
7. Wait 5 seconds
8. Click "🔄 New Session"
9. Status back to "Connected" (green dot)
10. Can send messages again
```

---

## Debugging with Test UI

### View Logs
The log console shows real-time events:
```
[10:30:45] INFO: Test interface loaded
[10:30:46] INFO: Creating new session with language: en
[10:30:47] INFO: Session created: abc123-def456...
[10:30:50] INFO: Sending message: "What dogs are available..."
[10:30:52] INFO: Received response (245 chars)
```

### Inspect Network Requests
Open browser DevTools (F12):
1. Go to Network tab
2. Send a message
3. Look for POST request to `/api/v1/chat`
4. View Request/Response:
   - Request payload
   - Response data
   - Status codes
   - Timing

### Check Session State
In browser console (F12 → Console):
```javascript
// Current session ID
console.log(sessionId);

// Message count
console.log(messageCount);
```

---

## Common Issues & Solutions

### Issue: "Failed to create session"
**Cause**: API not running or wrong endpoint

**Solution**:
```bash
# Check API is running
curl http://localhost:8000/health

# Check logs
docker-compose logs api

# Restart API
docker-compose restart api
```

### Issue: "No active session. Please create a new session first."
**Cause**: Session expired or was ended

**Solution**:
- Click "🔄 New Session" button

### Issue: Chatbot responds with "I don't have information..."
**Cause**: No data synced to Google File Search

**Solution**:
```bash
# Scrape animals
curl -X POST http://localhost:8000/api/v1/admin/scrape \
  -H "Content-Type: application/json" \
  -d '{"job_type": "animals"}'

# Sync to Google
curl -X POST http://localhost:8000/api/v1/admin/sync \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "animals"}'

# Refresh in chatbot
curl -X POST http://localhost:8000/api/v1/chat/refresh-files

# Create new session in UI
```

### Issue: Responses are slow
**Cause**: Google API processing time

**Expected**: 2-5 seconds per response is normal

**If longer than 10 seconds**:
- Check Google API quota
- Check network connection
- Review API logs: `docker-compose logs api`

### Issue: Status shows "Disconnected"
**Cause**: Cannot reach API

**Solution**:
1. Verify API endpoint in sidebar (should be `http://localhost:8000/api/v1/chat`)
2. Check API is running: `docker-compose ps`
3. Test health: `curl http://localhost:8000/health`
4. Check CORS settings in `.env` (should allow localhost)

---

## Advanced Testing

### Load Testing

Send multiple concurrent requests:

```javascript
// In browser console while test UI is open
for (let i = 0; i < 10; i++) {
  setTimeout(() => {
    document.getElementById('messageInput').value = `Test message ${i}`;
    sendMessage();
  }, i * 1000);
}
```

### API Direct Testing

```bash
# Create session
SESSION_ID=$(curl -s -X POST "http://localhost:8000/api/v1/chat/session?language=en" | jq -r '.session_id')

echo "Session: $SESSION_ID"

# Send message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"What dogs are available?\",
    \"session_id\": \"$SESSION_ID\",
    \"language\": \"en\"
  }" | jq

# Get session info
curl "http://localhost:8000/api/v1/chat/session/$SESSION_ID" | jq

# End session
curl -X DELETE "http://localhost:8000/api/v1/chat/session/$SESSION_ID"
```

---

## Next Steps After Testing

Once basic tests pass:

1. **Scrape More Content**
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/scrape \
     -H "Content-Type: application/json" \
     -d '{"job_type": "full"}'
   ```

2. **Sync All Content**
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/sync \
     -H "Content-Type: application/json" \
     -d '{"sync_type": "all"}'
   ```

3. **Test Widget**
   - Open `widget/example.html`
   - Test embedded widget

4. **Monitor Scheduled Jobs**
   ```bash
   docker-compose logs scraper -f
   ```

5. **Review Database**
   ```bash
   docker-compose exec db psql -U spca -d spca
   ```

---

## Automated Testing Script

Save as `quick_test.sh`:

```bash
#!/bin/bash

echo "=== SPCA Chatbot Quick Test ==="

# 1. Health check
echo -e "\n1. Testing API health..."
curl -s http://localhost:8000/health | jq -r '.status'

# 2. Create session
echo -e "\n2. Creating session..."
SESSION_ID=$(curl -s -X POST "http://localhost:8000/api/v1/chat/session?language=en" | jq -r '.session_id')
echo "Session: $SESSION_ID"

# 3. Send test message
echo -e "\n3. Sending test message..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Hello, what can you help me with?\",
    \"session_id\": \"$SESSION_ID\",
    \"language\": \"en\"
  }")

echo "$RESPONSE" | jq -r '.response'

# 4. Check stats
echo -e "\n4. Checking stats..."
curl -s http://localhost:8000/api/v1/admin/stats | jq

echo -e "\n=== Test Complete ==="
```

Run with:
```bash
chmod +x quick_test.sh
./quick_test.sh
```

---

Happy Testing! 🧪🐾
