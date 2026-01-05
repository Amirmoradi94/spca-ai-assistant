# SPCA AI Assistant

AI-powered chatbot for the SPCA Montreal website that helps visitors find information about animals available for adoption and SPCA services.

## Features

- **Automated Web Scraping**: Crawls SPCA website for animal data and general content
- **Dual Scraping Strategy**:
  - General content with Crawl4AI
  - Animal pages with Zyte API + BeautifulSoup for detailed extraction
- **PostgreSQL Database**: Stores animal data with change detection
- **Google Gemini File Search**: RAG-powered chatbot with automatic chunking and embedding
- **FastAPI Backend**: RESTful API for chat interactions
- **Embeddable Widget**: JavaScript widget with EN/FR bilingual support
- **Scheduled Updates**: Automatic scraping every 4 hours for animals, daily for content
- **Docker Deployment**: Multi-container setup with PostgreSQL

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SPCA AI ASSISTANT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ URL Discovery│───▶│ Content      │───▶│ Animal       │      │
│  │ (USP Parser) │    │ Scraper      │    │ Scraper      │      │
│  │              │    │ (Crawl4AI)   │    │ (Zyte+BS4)   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ URL          │    │ Markdown     │    │ PostgreSQL   │      │
│  │ Categorizer  │    │ Files (.txt) │    │ Database     │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│                             │                   │              │
│                             └─────────┬─────────┘              │
│                                       ▼                        │
│                      ┌────────────────────────────┐            │
│                      │   Content Sync Service     │            │
│                      └────────────────────────────┘            │
│                                       │                        │
│                                       ▼                        │
│                      ┌────────────────────────────┐            │
│                      │ Google Gemini File Search  │            │
│                      └────────────────────────────┘            │
│                                       │                        │
│                                       ▼                        │
│                      ┌────────────────────────────┐            │
│                      │   FastAPI Chatbot Backend  │            │
│                      └────────────────────────────┘            │
│                                       │                        │
│                                       ▼                        │
│                      ┌────────────────────────────┐            │
│                      │   Embeddable JS Widget     │            │
│                      └────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Zyte API key (optional, for production scraping)
- Google Gemini API key

### 1. Clone and Setup

```bash
git clone <repository-url>
cd spca-ai-assistant

# Create .env file from example
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 2. Configure Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional (for production)
ZYTE_API_KEY=your_zyte_api_key_here

# Database (already configured for Docker)
DATABASE_URL=postgresql+asyncpg://spca:spca_password@db:5432/spca
```

### 3. Start with Docker

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

Services will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

### 4. Initialize Database

```bash
# The database will be initialized automatically on first run
# To manually reset:
docker-compose exec api python -c "from src.database.session import init_db; import asyncio; asyncio.run(init_db())"
```

## Usage

### Running Scrapers

#### Manual Scrape via API

```bash
# Scrape only animals
curl -X POST http://localhost:8000/api/v1/admin/scrape \
  -H "Content-Type: application/json" \
  -d '{"job_type": "animals"}'

# Scrape only content
curl -X POST http://localhost:8000/api/v1/admin/scrape \
  -H "Content-Type: application/json" \
  -d '{"job_type": "content"}'

# Full scrape (sitemap + animals + content)
curl -X POST http://localhost:8000/api/v1/admin/scrape \
  -H "Content-Type: application/json" \
  -d '{"job_type": "full"}'
```

#### Manual Scrape via Python

```bash
# Inside container
docker-compose exec scraper python -m src.pipeline.orchestrator
```

### Syncing to Google File Search

```bash
# Sync animals
curl -X POST http://localhost:8000/api/v1/admin/sync \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "animals"}'

# Sync all content
curl -X POST http://localhost:8000/api/v1/admin/sync \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "all"}'
```

### Using the Chat API

```bash
# Create a session
curl -X POST http://localhost:8000/api/v1/chat/session?language=en

# Send a message
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What dogs are available for adoption?",
    "session_id": "your-session-id",
    "language": "en"
  }'
```

### Embedding the Widget

Add to your HTML before `</body>`:

```html
<script>
    window.SPCA_CHAT_CONFIG = {
        apiEndpoint: 'http://localhost:8000/api/v1/chat',
        theme: { primaryColor: '#0066cc' },
        language: 'auto'
    };
</script>
<link rel="stylesheet" href="/widget/src/styles.css">
<script src="/widget/src/index.js" data-auto-init="true"></script>
```

See `widget/example.html` for a complete example.

## Development

### Without Docker

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL (or use SQLite)
# Update DATABASE_URL in .env

# Initialize database
python -c "from src.database.session import init_db; import asyncio; asyncio.run(init_db())"

# Run API server
python -m src.api.main

# Run scraper service
python -m src.pipeline.scheduler
```

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# With coverage
pytest --cov=src tests/
```

## Configuration

### Scraping Schedule

Edit `config/config.yaml`:

```yaml
scheduling:
  animal_scrape_hours: 4      # Every 4 hours
  content_scrape_hour: 2      # Daily at 2 AM
  sitemap_refresh_day: "sun"  # Weekly on Sunday
```

### Animal Scraping Sources

The system scrapes from these adoption listing URLs:
- https://www.spca.com/en/adoption/cats-for-adoption/
- https://www.spca.com/en/adoption/dogs-for-adoption/
- https://www.spca.com/en/adoption/rabbits-for-adoption/
- https://www.spca.com/en/adoption/birds-for-adoption/
- https://www.spca.com/en/adoption/small-animals-for-adoption/

### Database Schema

Key tables:
- `animals`: Animal data with sync status
- `scrape_jobs`: Job tracking
- `scraped_urls`: URL tracking with status
- `sync_log`: Google File Search sync history

## API Endpoints

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
| POST | `/api/v1/admin/sync` | Trigger sync to Google |
| GET | `/api/v1/admin/stats` | Get system statistics |

### Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | API info |

Full API documentation: http://localhost:8000/docs

## Project Structure

```
spca-ai-assistant/
├── src/
│   ├── api/                    # FastAPI application
│   ├── chatbot/                # Gemini chatbot logic
│   ├── database/               # SQLAlchemy models & repositories
│   ├── pipeline/               # Scraping orchestration & scheduling
│   ├── scrapers/               # Web scraping modules
│   ├── processors/             # Content processors
│   ├── sync/                   # Google File Search sync
│   └── utils/                  # Utilities (config, logging, etc.)
├── widget/                     # Embeddable chat widget
│   ├── src/
│   │   ├── index.js            # Widget JavaScript
│   │   ├── styles.css          # Widget styles
│   │   └── i18n/               # Translations (EN/FR)
│   └── example.html            # Widget demo
├── content/                    # Scraped content storage
│   ├── animals/                # Animal text files
│   └── general/                # General content
├── config/                     # Configuration files
├── tests/                      # Test suite
├── docker-compose.yml          # Docker services
├── Dockerfile                  # Container image
└── requirements.txt            # Python dependencies
```

## Troubleshooting

### Database Connection Issues

```bash
# Check database status
docker-compose ps db

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Scraper Not Running

```bash
# Check scraper logs
docker-compose logs scraper

# Restart scraper
docker-compose restart scraper
```

### API Errors

```bash
# View API logs
docker-compose logs api

# Check health
curl http://localhost:8000/health
```

## Production Deployment

### Security Considerations

1. **Protect Admin Endpoints**: Add authentication middleware
2. **CORS Configuration**: Update `CORS_ORIGINS` in `.env`
3. **API Rate Limiting**: Implement rate limiting
4. **Environment Variables**: Use secrets management
5. **HTTPS**: Deploy behind reverse proxy with SSL

### Recommended Setup

```
[Internet]
    ↓
[Load Balancer / Reverse Proxy (Nginx/Traefik)]
    ↓
[Docker Swarm / Kubernetes]
    ├── API Service (replicas: 3)
    ├── Scraper Service (replicas: 1)
    └── PostgreSQL (managed service)
```

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.
