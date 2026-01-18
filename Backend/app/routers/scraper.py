import os
import traceback
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Any

from app.services.job_scraper.config import settings
from app.services.job_scraper.models import (
    CompanySearchRequest,
    CompanyInterviewDataResponse,
    ErrorResponse,
    HealthResponse,
    ScrapingProgressUpdate,
)
from app.services.job_scraper.service import ScraperService
from app.utils.key_manager import get_key_count

router = APIRouter()

# ScraperService is now initialized per request for key rotation


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Scraper Health"],
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", version=settings.api_version)


@router.post(
    "/scrape",
    response_model=CompanyInterviewDataResponse,
    tags=["Scraping"],
)
async def scrape_company_data(
    request: CompanySearchRequest,
    background_tasks: BackgroundTasks,
) -> CompanyInterviewDataResponse:
    # Initialize service per request to handle key rotation
    if os.environ.get("DISABLE_KEY_ROTATION") == "true":
        max_retries = 1
    else:
        max_retries = max(
            get_key_count("LLM_SERVICE_API_KEY"),
            get_key_count("LLM_API_KEY"),
            get_key_count("GROQ_API_KEY"),
            1,
        )
    last_error = None

    for attempt in range(max_retries):
        try:
            service = ScraperService(session_id=request.session_id, attempt=attempt)
            result = await service.scrape_company_data(request)
            background_tasks.add_task(
                service.background_enrichment, request.company_name
            )
            return result
        except Exception:
            print(f"⚠️ [SCRAPE] Attempt {attempt} failed:")
            traceback.print_exc()
            last_error = "Check backend logs for traceback"
            continue

    traceback.print_exc()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to scrape company data after {max_retries} attempts: {str(last_error)}",
    )


@router.post(
    "/scrape/stream",
    tags=["Scraping"],
)
async def scrape_company_data_stream(
    request: CompanySearchRequest,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        if os.environ.get("DISABLE_KEY_ROTATION") == "true":
            max_retries = 1
        else:
            max_retries = max(
                get_key_count("LLM_SERVICE_API_KEY"),
                get_key_count("LLM_API_KEY"),
                get_key_count("GROQ_API_KEY"),
                1,
            )
        last_error = None

        for attempt in range(max_retries):
            try:
                service = ScraperService(session_id=request.session_id, attempt=attempt)
                background_tasks.add_task(
                    service.background_enrichment, request.company_name
                )

                async for update in service.scrape_company_data_stream(request):
                    event_type = (
                        "complete" if update.status == "complete" else "progress"
                    )
                    data = update.model_dump_json()
                    yield f"event: {event_type}\ndata: {data}\n\n"

                # If we get here successfully, we can return
                return

            except Exception as e:
                print(f"⚠️ [STREAM] Attempt {attempt} failed: {e}")
                last_error = e
                if attempt == max_retries - 1:
                    error_update = ScrapingProgressUpdate(
                        status="error",
                        message=f"Error after {max_retries} attempts: {str(last_error)}",
                        progress_percent=0,
                    )
                    yield f"event: error\ndata: {error_update.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
