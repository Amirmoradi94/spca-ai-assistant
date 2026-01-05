# SPCA Chat Widget

Embeddable chat widget for the SPCA website with bilingual support (EN/FR).

## Features

- **Bilingual**: Automatic language detection (English/French)
- **Responsive**: Works on desktop and mobile
- **Customizable**: Theme colors and position
- **Session Management**: Maintains conversation context
- **Suggested Questions**: Helpful prompts for users
- **Typing Indicator**: Shows when bot is responding

## Installation

### Option 1: Auto-Initialize (Recommended)

Add this code before the closing `</body>` tag on your website:

```html
<script>
    window.SPCA_CHAT_CONFIG = {
        apiEndpoint: 'https://api.spca-assistant.com/api/v1/chat',
        theme: {
            primaryColor: '#0066cc'
        },
        language: 'auto' // or 'en' or 'fr'
    };
</script>
<link rel="stylesheet" href="https://cdn.spca-assistant.com/widget/styles.css">
<script src="https://cdn.spca-assistant.com/widget/index.js" data-auto-init="true"></script>
```

### Option 2: Manual Initialize

```html
<link rel="stylesheet" href="widget/src/styles.css">
<script src="widget/src/index.js"></script>
<script>
    // Initialize manually
    const chatWidget = new SPCAChatWidget({
        apiEndpoint: 'http://localhost:8000/api/v1/chat',
        theme: {
            primaryColor: '#0066cc'
        },
        language: 'auto'
    });
</script>
```

## Configuration Options

```javascript
{
    // Required: API endpoint
    apiEndpoint: 'https://api.spca-assistant.com/api/v1/chat',

    // Theme customization
    theme: {
        primaryColor: '#0066cc',     // Primary color
        headerBg: '#0066cc'          // Header background
    },

    // Language: 'auto', 'en', or 'fr'
    // 'auto' detects from URL path or HTML lang attribute
    language: 'auto',

    // Position: 'bottom-right', 'bottom-left', 'top-right', 'top-left'
    position: 'bottom-right',

    // Show greeting message on load
    showGreeting: true,

    // Show suggested questions
    showSuggestions: true
}
```

## Language Detection

The widget automatically detects the page language using:

1. URL path (e.g., `/fr/` for French)
2. HTML `lang` attribute
3. Falls back to English

## Development

### Building

For production, you would bundle and minify:

```bash
# Install dependencies
npm install

# Build
npm run build
```

### File Structure

```
widget/
├── src/
│   ├── index.js          # Main widget code
│   ├── styles.css        # Widget styles
│   └── i18n/
│       ├── en.json       # English translations
│       └── fr.json       # French translations
├── dist/                 # Built files (minified)
└── README.md
```

## API Requirements

The widget expects the following API endpoints:

- `POST /api/v1/chat/session?language={lang}` - Create session
- `POST /api/v1/chat` - Send message
  ```json
  {
    "message": "string",
    "session_id": "string",
    "language": "en|fr"
  }
  ```

Response format:
```json
{
  "response": "string",
  "session_id": "string",
  "sources": [
    {
      "file": "string",
      "snippet": "string"
    }
  ],
  "suggested_questions": ["string"]
}
```

## Browser Support

- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Mobile browsers (iOS Safari, Chrome Android)

## License

MIT
