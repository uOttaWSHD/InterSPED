"""
Pydantic models/contracts for the JobScraper API.
These define the request and response schemas for all endpoints.
"""
from __future__ import annotations
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# REQUEST MODELS
# ============================================================================

class CompanySearchRequest(BaseModel):
    """
    Request to search for company information and interview materials.
    
    Example:
        {
            "company_name": "Google",
            "job_posting_url": "https://careers.google.com/jobs/...",
            "position": "Software Engineer"
        }
    """
    company_name: str = Field(
        ..., 
        description="Name of the company to research",
        examples=["Google", "Microsoft", "Amazon"]
    )
    job_posting_url: Optional[HttpUrl] = Field(
        None,
        description="Optional URL to a specific job posting for more targeted insights"
    )
    position: Optional[str] = Field(
        None,
        description="Optional job position/role for more specific interview prep",
        examples=["Software Engineer", "Product Manager", "Data Scientist"]
    )


# ============================================================================
# RESPONSE MODELS - Nested Data Structures
# ============================================================================

class CompanyOverview(BaseModel):
    """Basic company information extracted from various sources."""
    name: str = Field(..., description="Official company name")
    industry: Optional[str] = Field(None, description="Primary industry/sector")
    size: Optional[str] = Field(None, description="Company size (e.g., '10,000-50,000 employees')")
    headquarters: Optional[str] = Field(None, description="Company headquarters location")
    mission: Optional[str] = Field(None, description="Company mission statement")
    culture: Optional[str] = Field(None, description="Company culture description")
    recent_news: list[str] = Field(
        default_factory=list,
        description="Recent company news or achievements"
    )


class InterviewQuestion(BaseModel):
    """A single interview question with metadata."""
    question: str = Field(..., description="The interview question text")
    category: Literal[
        "behavioral", 
        "technical", 
        "situational", 
        "culture_fit",
        "role_specific",
        "problem_solving"
    ] = Field(..., description="Category of the question")
    difficulty: Optional[Literal["easy", "medium", "hard"]] = Field(
        None,
        description="Difficulty level if applicable"
    )
    tips: Optional[str] = Field(
        None,
        description="Tips for answering this question"
    )


class InterviewStage(BaseModel):
    """Information about a specific interview stage/round."""
    stage_name: str = Field(
        ..., 
        description="Name of the interview stage",
        examples=["Phone Screen", "Technical Round", "Onsite", "Final Round"]
    )
    description: Optional[str] = Field(
        None,
        description="What to expect in this stage"
    )
    duration: Optional[str] = Field(
        None,
        description="Typical duration",
        examples=["30 minutes", "1-2 hours", "Full day"]
    )
    format: Optional[str] = Field(
        None,
        description="Interview format",
        examples=["Video call", "In-person", "Coding challenge", "Whiteboard"]
    )


class InterviewProcess(BaseModel):
    """Complete interview process information."""
    stages: list["InterviewStage"] = Field(  # type: ignore[valid-type]
        default_factory=list,
        description="List of interview stages in order"
    )
    total_duration: Optional[str] = Field(
        None,
        description="Total time from application to offer",
        examples=["2-4 weeks", "1-2 months"]
    )
    preparation_tips: list[str] = Field(
        default_factory=list,
        description="General preparation tips for this company's interviews"
    )


class TechnicalRequirements(BaseModel):
    """Technical skills and requirements for the role."""
    programming_languages: list[str] = Field(
        default_factory=list,
        description="Required or preferred programming languages"
    )
    frameworks_tools: list[str] = Field(
        default_factory=list,
        description="Frameworks, tools, or technologies mentioned"
    )
    concepts: list[str] = Field(
        default_factory=list,
        description="Technical concepts to study",
        examples=["System Design", "Data Structures", "Algorithms", "OOP"]
    )
    experience_level: Optional[str] = Field(
        None,
        description="Required experience level",
        examples=["Entry-level", "2-5 years", "Senior (5+ years)"]
    )


class InterviewInsights(BaseModel):
    """Deep insights about the interview and what to expect."""
    common_questions: list["InterviewQuestion"] = Field(  # type: ignore[valid-type]
        default_factory=list,
        description="Commonly asked interview questions at this company"
    )
    interview_process: InterviewProcess = Field(
        ...,
        description="Structure and flow of the interview process"
    )
    technical_requirements: Optional[TechnicalRequirements] = Field(
        None,
        description="Technical skills and requirements (if applicable)"
    )
    what_they_look_for: list[str] = Field(
        default_factory=list,
        description="Key qualities and traits the company values in candidates"
    )
    red_flags_to_avoid: list[str] = Field(
        default_factory=list,
        description="Things to avoid saying or doing in the interview"
    )
    salary_range: Optional[str] = Field(
        None,
        description="Expected salary range if available"
    )


# ============================================================================
# MAIN RESPONSE MODELS
# ============================================================================

class CompanyInterviewDataResponse(BaseModel):
    """
    Complete response containing all scraped company and interview data.
    
    This is the main contract returned by POST /api/v1/scrape
    """
    success: bool = Field(..., description="Whether the scraping was successful")
    company_overview: CompanyOverview = Field(
        ...,
        description="General company information"
    )
    interview_insights: InterviewInsights = Field(
        ...,
        description="Interview preparation materials and insights"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="URLs of sources used to compile this information"
    )
    session_id: str = Field(
        ...,
        description="Yellowcake session ID for tracking"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the scraping process"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = Field(False, description="Always False for errors")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")


# ============================================================================
# STREAMING RESPONSE MODELS (for SSE updates)
# ============================================================================

class ScrapingProgressUpdate(BaseModel):
    """Progress update during scraping (for SSE streaming)."""
    status: Literal["started", "in_progress", "complete", "error"] = Field(
        ...,
        description="Current status of the scraping operation"
    )
    message: str = Field(..., description="Human-readable status message")
    progress_percent: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Progress percentage if available"
    )
    session_id: str | None = Field(default=None, description="Yellowcake session ID")
    data: CompanyInterviewDataResponse | None = Field(
        default=None,
        description="Complete data (only present when status='complete')"
    )
