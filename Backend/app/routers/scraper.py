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

router = APIRouter()

# Initialize service (lazy loading might be better if it takes time, but standard is fine)
# We handle initialization error if config is missing
try:
    scraper_service = ScraperService()
except Exception as e:
    print(f"Failed to initialize ScraperService: {e}")
    scraper_service = None


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
    if not scraper_service:
        raise HTTPException(status_code=500, detail="Scraper service not initialized")
    try:
        result = await scraper_service.scrape_company_data(request)
        background_tasks.add_task(
            scraper_service.background_enrichment, request.company_name
        )
        return result
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape company data: {str(e)}",
        )


@router.post(
    "/scrape/stream",
    tags=["Scraping"],
)
async def scrape_company_data_stream(
    request: CompanySearchRequest,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    if not scraper_service:
        raise HTTPException(status_code=500, detail="Scraper service not initialized")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            background_tasks.add_task(
                scraper_service.background_enrichment, request.company_name
            )

            async for update in scraper_service.scrape_company_data_stream(request):
                event_type = "complete" if update.status == "complete" else "progress"
                data = update.model_dump_json()
                yield f"event: {event_type}\ndata: {data}\n\n"
        except Exception as e:
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
            "X-Accel-Buffering": "no",
        },
    )
