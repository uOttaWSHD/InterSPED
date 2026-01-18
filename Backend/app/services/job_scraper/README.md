# JobScraper API

AI-powered company research and interview preparation API built with FastAPI, Pydantic, and Yellowcake.

## Overview

JobScraper helps job seekers prepare for interviews by automatically scraping and compiling:
- Company information (mission, culture, size, etc.)
- Common interview questions
- Interview process and stages
- Technical requirements
- Preparation tips and insights

## Features

- 🎯 **Clear Pydantic Contracts** - All request/response schemas are strongly typed
- 📡 **SSE Streaming** - Real-time progress updates for long-running scrapes
- 📚 **Auto-generated Swagger Docs** - Interactive API documentation at `/docs`
- 🔄 **Multi-source Scraping** - Aggregates data from multiple sources using Yellowcake
- ⚡ **FastAPI** - Modern, fast, async Python web framework

## API Contracts

### Request: `CompanySearchRequest`

```json
{
  "company_name": "Google",
  "job_posting_url": "https://careers.google.com/jobs/...", // optional
  "position": "Software Engineer" // optional
}
```

### Response: `CompanyInterviewDataResponse`

```json
{
  "success": true,
  "company_overview": {
    "name": "Google",
    "industry": "Technology",
    "size": "100,000+ employees",
    "headquarters": "Mountain View, CA",
    "mission": "Organize the world's information",
    "culture": "Innovation-focused, data-driven",
    "recent_news": ["Launched Gemini AI", "Expanded cloud services"]
  },
  "interview_insights": {
    "common_questions": [
      {
        "question": "Tell me about a time you solved a complex problem",
        "category": "behavioral",
        "difficulty": "medium",
        "tips": "Use the STAR method"
      }
    ],
    "interview_process": {
      "stages": [
        {
          "stage_name": "Phone Screen",
          "description": "30-minute recruiter call",
          "duration": "30 minutes",
          "format": "Video call"
        }
      ],
      "total_duration": "4-6 weeks",
      "preparation_tips": ["Practice coding on whiteboard", "Review system design"]
    },
    "technical_requirements": {
      "programming_languages": ["Python", "Java", "C++"],
      "frameworks_tools": ["TensorFlow", "Kubernetes"],
      "concepts": ["Algorithms", "System Design", "ML"],
      "experience_level": "3-5 years"
    },
    "what_they_look_for": ["Problem-solving", "Leadership", "Innovation"],
    "red_flags_to_avoid": ["Negativity", "Lack of curiosity"],
    "salary_range": "$150k - $250k"
  },
  "sources": ["https://..."],
  "session_id": "yellowcake-session-id",
  "metadata": {
    "total_sources_scraped": 3,
    "yellowcake_sessions": ["session-1", "session-2", "session-3"]
  }
}
```

## Endpoints

### `GET /health`
Health check endpoint.

**Response:** `HealthResponse`

### `POST /api/v1/scrape`
Main endpoint to scrape company data. Waits for all scraping to complete.

**Request Body:** `CompanySearchRequest`  
**Response:** `CompanyInterviewDataResponse`

### `POST /api/v1/scrape/stream`
Stream scraping progress via Server-Sent Events (SSE).

**Request Body:** `CompanySearchRequest`  
**Response:** SSE stream with `ScrapingProgressUpdate` events

**SSE Events:**
- `progress` - In-progress updates with percentage
- `complete` - Final data with full `CompanyInterviewDataResponse`
- `error` - Error information

### `GET /api/v1/examples`
View example request/response contracts.

## Setup

### Prerequisites
- Python 3.13+ (or compatible version)
- [uv](https://github.com/astral-sh/uv) package manager
- Yellowcake API key from [yellowcake.dev](https://yellowcake.dev)

### Installation

1. Clone the repository:
```bash
cd /path/to/JobScraper
```

2. Dependencies are already installed via `uv init` and `uv add`

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your Yellowcake API key
```

### Running the API

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or use the built-in runner:
```bash
uv run python main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Usage Examples

### cURL - Basic Request
```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Google",
    "position": "Software Engineer"
  }'
```

### cURL - Stream Request
```bash
curl -N -X POST "http://localhost:8000/api/v1/scrape/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Microsoft",
    "job_posting_url": "https://careers.microsoft.com/job/1234567",
    "position": "Product Manager"
  }'
```

### Python Client
```python
import httpx
import json

async def scrape_company():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/scrape",
            json={
                "company_name": "Amazon",
                "position": "Data Scientist"
            },
            timeout=300.0  # 5 minutes
        )
        data = response.json()
        print(json.dumps(data, indent=2))

# Or use streaming
async def scrape_company_stream():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/scrape/stream",
            json={"company_name": "Apple", "position": "iOS Engineer"},
            timeout=300.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    print(f"Progress: {data.get('message')}")
                    if data.get("status") == "complete":
                        print("Final data:", data.get("data"))
```

### JavaScript/TypeScript
```typescript
// Non-streaming
const response = await fetch('http://localhost:8000/api/v1/scrape', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    company_name: 'Tesla',
    position: 'Mechanical Engineer'
  })
});
const data = await response.json();

// Streaming with SSE
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/scrape/stream',
  {
    method: 'POST',
    body: JSON.stringify({ company_name: 'Netflix' })
  }
);

eventSource.addEventListener('progress', (e) => {
  const update = JSON.parse(e.data);
  console.log(`Progress: ${update.progress_percent}%`);
});

eventSource.addEventListener('complete', (e) => {
  const result = JSON.parse(e.data);
  console.log('Complete:', result.data);
  eventSource.close();
});
```

## Project Structure

```
JobScraper/
├── main.py              # FastAPI application and endpoints
├── models.py            # Pydantic models/contracts
├── service.py           # Yellowcake service and scraping logic
├── config.py            # Configuration management
├── .env                 # Environment variables (not in git)
├── .env.example         # Example environment config
├── pyproject.toml       # uv project configuration
├── README.md            # This file
└── YELLOWCAKE.md        # Yellowcake API documentation
```

## Architecture

1. **models.py** - Defines all Pydantic schemas:
   - `CompanySearchRequest` - Input contract
   - `CompanyInterviewDataResponse` - Main output contract
   - `CompanyOverview`, `InterviewInsights`, etc. - Nested data structures
   - `ScrapingProgressUpdate` - SSE streaming updates

2. **service.py** - Business logic:
   - `YellowcakeService` - Handles Yellowcake API interactions
   - Multi-source scraping strategy
   - Data aggregation and transformation

3. **main.py** - FastAPI endpoints:
   - RESTful API routes
   - Request validation
   - Error handling
   - SSE streaming

4. **config.py** - Environment configuration using Pydantic Settings

## Notes

- **Scraping Duration**: Typically 30 seconds to 5 minutes depending on sources and Yellowcake API
- **Rate Limiting**: Yellowcake handles throttling; avoid concurrent requests for same company
- **Data Quality**: Results depend on publicly available information
- **Cost**: Yellowcake API calls are metered - monitor your usage

## Development

### Type Checking
The codebase uses Pydantic for runtime validation and type hints for static analysis.

### Testing
```bash
# Add pytest
uv add --dev pytest pytest-asyncio httpx

# Run tests (create test files first)
uv run pytest
```

## License

MIT

## Support

For Yellowcake API issues, contact hello@yellowcake.dev or join their Discord.

For this API, open an issue on GitHub.
