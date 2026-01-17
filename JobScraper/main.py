"""
JobScraper API - Main FastAPI Application

This API scrapes company information and generates interview preparation materials
using AI-powered web scraping via Yellowcake.

Clear Contracts:
- POST /api/v1/scrape - Main endpoint to scrape company data (returns full response)
- POST /api/v1/scrape/stream - Stream scraping progress via SSE
- GET /health - Health check

All request/response schemas are defined in models.py using Pydantic.
Swagger docs available at /docs
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator, Any

from config import settings
from models import (
    CompanySearchRequest,
    CompanyInterviewDataResponse,
    ErrorResponse,
    HealthResponse,
    ScrapingProgressUpdate,
)
from service import ScraperService

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
scraper_service = ScraperService()


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to docs."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
)
async def health_check() -> HealthResponse:
    """
    Check if the API is running and healthy.

    Returns:
        HealthResponse with status and version
    """
    return HealthResponse(status="healthy", version=settings.api_version)


@app.post(
    "/api/v1/scrape",
    response_model=CompanyInterviewDataResponse,
    responses={
        200: {
            "description": "Successfully scraped company data",
            "model": CompanyInterviewDataResponse,
        },
        400: {"description": "Invalid request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["Scraping"],
    summary="Scrape company interview data",
    description="""
    **Main endpoint to scrape company information and interview preparation materials.**
    
    Provide a company name (required) and optionally:
    - A specific job posting URL for targeted insights
    - A position/role for role-specific preparation
    
    The API will:
    1. Search multiple sources for company information
    2. Extract interview questions and processes
    3. Identify technical requirements
    4. Compile preparation tips and insights
    
    **Returns a complete CompanyInterviewDataResponse** with:
    - Company overview (mission, culture, size, etc.)
    - Interview insights (questions, process, tips)
    - Technical requirements (if applicable)
    - Source URLs used
    
    This endpoint waits for all scraping to complete before returning.
    Use `/api/v1/scrape/stream` for real-time progress updates.
    """,
)
async def scrape_company_data(
    request: CompanySearchRequest,
    background_tasks: BackgroundTasks,
) -> CompanyInterviewDataResponse:
    """
    Scrape company interview data and return complete results.

    Args:
        request: CompanySearchRequest with company name and optional details
        background_tasks: FastAPI background tasks

    Returns:
        CompanyInterviewDataResponse with all scraped data

    Raises:
        HTTPException: If scraping fails
    """
    try:
        # 1. Execute the main pipeline (Fast Path)
        # This will scrape 3 random problems immediately
        result = await scraper_service.scrape_company_data(request)

        # 2. Schedule the remaining problems in the background (Slow Path)
        # This updates the cache for future requests
        background_tasks.add_task(
            scraper_service.background_enrichment, request.company_name
        )

        return result
    except Exception as e:
        import traceback

        traceback.print_exc()  # Print full stack trace to console
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape company data: {str(e)}",
        )


@app.post(
    "/api/v1/scrape/stream",
    responses={
        200: {
            "description": "Server-Sent Events stream of scraping progress",
            "content": {
                "text/event-stream": {
                    "example": 'event: progress\ndata: {"status":"in_progress","message":"Scraping..."}\n\n'
                }
            },
        }
    },
    tags=["Scraping"],
    summary="Stream scraping progress via SSE",
    description="""
    **Stream real-time progress updates while scraping company data.**
    
    This endpoint uses Server-Sent Events (SSE) to stream progress updates
    including:
    - Status updates (started, in_progress, complete, error)
    - Progress percentage (0-100)
    - Human-readable messages
    - Final complete data when done
    
    **SSE Event Format:**
    ```
    event: progress
    data: {"status": "in_progress", "message": "Scraping...", "progress_percent": 50}
    
    event: complete
    data: {"status": "complete", "data": {...full CompanyInterviewDataResponse...}}
    ```
    
    Use this for better UX when scraping takes time (typically 30s - 5min).
    """,
)
async def scrape_company_data_stream(
    request: CompanySearchRequest,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    """
    Stream scraping progress using Server-Sent Events.

    Args:
        request: CompanySearchRequest with company name and optional details
        background_tasks: FastAPI background tasks

    Returns:
        StreamingResponse with SSE events
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from scraping progress."""
        try:
            # Trigger background enrichment as soon as we start streaming
            background_tasks.add_task(
                scraper_service.background_enrichment, request.company_name
            )

            async for update in scraper_service.scrape_company_data_stream(request):
                # Format as SSE
                event_type = "complete" if update.status == "complete" else "progress"
                data = update.model_dump_json()
                yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
            # Send error event
            error_update = ScrapingProgressUpdate(
                status="error", message=f"Error: {str(e)}", progress_percent=0
            )
            yield f"event: error\ndata: {error_update.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ============================================================================
# EXAMPLE REQUEST CONTRACTS
# ============================================================================


@app.get(
    "/api/v1/examples",
    tags=["Documentation"],
    summary="View example requests and responses",
    description="Get example JSON contracts for API requests",
)
async def get_examples() -> dict[str, Any]:
    """
    Return example requests to help users understand the API contracts.
    """
    return {
        "basic_request": {
            "company_name": "Google",
            "job_posting_url": None,
            "position": None,
        },
        "detailed_request": {
            "company_name": "Microsoft",
            "job_posting_url": "https://careers.microsoft.com/us/en/job/1234567/Software-Engineer",
            "position": "Software Engineer",
        },
        "example_response_structure": {
            "success": True,
            "company_overview": {
                "name": "Example Corp",
                "industry": "Technology",
                "size": "10,000-50,000 employees",
                "headquarters": "San Francisco, CA",
                "mission": "To organize the world's information",
                "culture": "Innovation-focused, collaborative",
                "recent_news": ["Launched new product", "Expanded to EMEA"],
            },
            "interview_insights": {
                "common_questions": [
                    {
                        "question": "Tell me about yourself",
                        "category": "behavioral",
                        "difficulty": "easy",
                        "tips": "Focus on relevant experience",
                    }
                ],
                "interview_process": {
                    "stages": [
                        {
                            "stage_name": "Phone Screen",
                            "description": "Initial conversation with recruiter",
                            "duration": "30 minutes",
                            "format": "Video call",
                        }
                    ],
                    "total_duration": "2-4 weeks",
                    "preparation_tips": ["Practice coding", "Review STAR method"],
                },
                "technical_requirements": {
                    "programming_languages": ["Python", "Java"],
                    "frameworks_tools": ["React", "Docker"],
                    "concepts": ["System Design", "Algorithms"],
                    "experience_level": "2-5 years",
                },
                "what_they_look_for": ["Problem-solving", "Communication"],
                "red_flags_to_avoid": ["Bad-mouthing previous employers"],
                "salary_range": "$120k - $180k",
            },
            "sources": ["https://example.com/careers"],
            "session_id": "yellowcake-session-id",
            "metadata": {
                "total_sources_scraped": 3,
                "yellowcake_sessions": ["session-1", "session-2"],
            },
        },
    }


if __name__ == "__main__":
    pass
    # import uvicorn
    # uvicorn.run(
    #     "main:app",
    #     host="0.0.0.0",
    #     port=8000,
    #     reload=settings.debug
    # )
