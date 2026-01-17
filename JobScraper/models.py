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
        examples=["Google", "Microsoft", "Amazon"],
    )
    job_posting_url: Optional[HttpUrl] = Field(
        None,
        description="Optional URL to a specific job posting for more targeted insights",
    )
    position: Optional[str] = Field(
        None,
        description="Optional job position/role for more specific interview prep",
        examples=["Software Engineer", "Product Manager", "Data Scientist"],
    )


# ============================================================================
# RESPONSE MODELS - Nested Data Structures
# ============================================================================


class CompanyOverview(BaseModel):
    """Basic company information extracted from various sources."""

    name: str = Field(..., description="Official company name")
    industry: Optional[str] = Field(None, description="Primary industry/sector")
    size: Optional[str] = Field(
        None, description="Company size (e.g., '10,000-50,000 employees')"
    )
    headquarters: Optional[str] = Field(
        None, description="Company headquarters location"
    )
    mission: Optional[str] = Field(None, description="Company mission statement")
    culture: Optional[str] = Field(None, description="Company culture description")
    recent_news: list[str] = Field(
        default_factory=list, description="Recent company news or achievements"
    )


class InterviewQuestion(BaseModel):
    """
    A single interview question with comprehensive metadata and guidance.
    Designed to be detailed enough for interview reconstruction.
    """

    question: str = Field(..., description="The interview question text")
    category: Literal[
        "behavioral",
        "technical",
        "situational",
        "culture_fit",
        "role_specific",
        "problem_solving",
        "system_design",
        "coding",
        "leadership",
    ] = Field(..., description="Category of the question")
    difficulty: Optional[Literal["easy", "medium", "hard"]] = Field(
        None, description="Difficulty level if applicable"
    )
    tips: Optional[str] = Field(None, description="Tips for answering this question")
    sample_answer: Optional[str] = Field(
        None,
        description="Example of a strong answer using STAR (Situation, Task, Action, Result) or similar framework",
    )
    key_points_to_cover: list[str] = Field(
        default_factory=list,
        description="Critical points/themes that must be addressed in the answer",
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Typical follow-up questions the interviewer might ask",
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="Things to avoid in your answer that signal red flags",
    )
    company_specific_context: Optional[str] = Field(
        None,
        description="Why this company asks this question - what they're really looking for based on their values/culture",
    )


class InterviewStage(BaseModel):
    """
    Comprehensive information about a specific interview stage/round.
    Detailed enough to simulate the actual experience.
    """

    stage_name: str = Field(
        ...,
        description="Name of the interview stage",
        examples=["Phone Screen", "Technical Round", "Onsite", "Final Round"],
    )
    description: Optional[str] = Field(None, description="What to expect in this stage")
    duration: Optional[str] = Field(
        None,
        description="Typical duration",
        examples=["30 minutes", "1-2 hours", "Full day"],
    )
    format: Optional[str] = Field(
        None,
        description="Interview format",
        examples=["Video call", "In-person", "Coding challenge", "Whiteboard"],
    )
    interviewers: Optional[str] = Field(
        None,
        description="Who conducts this interview (e.g., 'Hiring Manager', '2-3 Senior Engineers', 'Panel of 4')",
    )
    focus_areas: list[str] = Field(
        default_factory=list,
        description="What this stage evaluates (e.g., 'Problem-solving', 'System design', 'Cultural fit')",
    )
    sample_questions: list[str] = Field(
        default_factory=list,
        description="Example questions asked in this specific stage",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="What the interviewers are looking for to pass this stage",
    )
    preparation_strategy: Optional[str] = Field(
        None, description="Specific preparation advice for this stage"
    )


class InterviewProcess(BaseModel):
    """Complete interview process information."""

    stages: list[InterviewStage] = Field(
        default_factory=list, description="List of interview stages in order"
    )
    total_duration: Optional[str] = Field(
        None,
        description="Total time from application to offer",
        examples=["2-4 weeks", "1-2 months"],
    )
    preparation_tips: list[str] = Field(
        default_factory=list,
        description="General preparation tips for this company's interviews",
    )


class TechnicalRequirements(BaseModel):
    """
    Technical skills and requirements for the role.
    Detailed enough to build a study plan.
    """

    programming_languages: list[str] = Field(
        default_factory=list, description="Required or preferred programming languages"
    )
    frameworks_tools: list[str] = Field(
        default_factory=list, description="Frameworks, tools, or technologies mentioned"
    )
    concepts: list[str] = Field(
        default_factory=list,
        description="Technical concepts to study",
        examples=["System Design", "Data Structures", "Algorithms", "OOP"],
    )
    experience_level: Optional[str] = Field(
        None,
        description="Required experience level",
        examples=["Entry-level", "2-5 years", "Senior (5+ years)"],
    )
    must_have_skills: list[str] = Field(
        default_factory=list, description="Critical skills that are non-negotiable"
    )
    nice_to_have_skills: list[str] = Field(
        default_factory=list, description="Skills that are beneficial but not required"
    )
    domain_knowledge: list[str] = Field(
        default_factory=list,
        description="Domain-specific knowledge areas (e.g., 'Financial Systems', 'Healthcare', 'Gaming')",
    )


class CodingProblem(BaseModel):
    """
    A specific coding problem asked in interviews at this company.
    Includes full details for practice and solution.
    """

    title: str = Field(..., description="Problem title/name")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ..., description="Problem difficulty"
    )
    problem_statement: str = Field(..., description="Full problem description")
    example_input: Optional[str] = Field(None, description="Example input")
    example_output: Optional[str] = Field(None, description="Example output")
    constraints: list[str] = Field(
        default_factory=list,
        description="Problem constraints (time/space complexity, input limits)",
    )
    leetcode_number: Optional[int] = Field(
        None, description="LeetCode problem number if applicable"
    )
    leetcode_url: Optional[str] = Field(
        None, description="Direct URL to LeetCode problem"
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Topics/patterns this problem covers (e.g., 'Dynamic Programming', 'Two Pointers')",
    )
    approach_hints: list[str] = Field(
        default_factory=list, description="Hints for solving the problem"
    )
    optimal_time_complexity: Optional[str] = Field(
        None,
        description="Expected optimal time complexity (e.g., 'O(n)', 'O(n log n)')",
    )
    optimal_space_complexity: Optional[str] = Field(
        None, description="Expected optimal space complexity"
    )
    frequency: Optional[Literal["very_common", "common", "occasional", "rare"]] = Field(
        None, description="How frequently this problem appears in interviews"
    )
    company_specific_notes: Optional[str] = Field(
        None,
        description="Company-specific context (e.g., 'They focus on follow-up optimizations', 'Expect live coding')",
    )


class SystemDesignQuestion(BaseModel):
    """
    A system design question with detailed evaluation criteria.
    """

    question: str = Field(
        ...,
        description="The system design question (e.g., 'Design Twitter', 'Design URL Shortener')",
    )
    scope: str = Field(
        ...,
        description="Expected scope and scale (e.g., '100M users', 'Global distribution')",
    )
    key_components: list[str] = Field(
        default_factory=list,
        description="Critical system components to discuss (e.g., 'Load Balancer', 'Cache', 'Database Sharding')",
    )
    evaluation_criteria: list[str] = Field(
        default_factory=list,
        description="What interviewers evaluate (e.g., 'Scalability considerations', 'Trade-off analysis')",
    )
    common_approaches: list[str] = Field(
        default_factory=list, description="Common architectural patterns or approaches"
    )
    follow_up_topics: list[str] = Field(
        default_factory=list,
        description="Deep-dive topics they might probe (e.g., 'CAP theorem', 'Consistency models')",
    )
    time_allocation: Optional[str] = Field(
        None,
        description="How to allocate time in the interview (e.g., '10min requirements, 30min design, 5min follow-ups')",
    )


class MockInterviewScenario(BaseModel):
    """
    A complete mock interview scenario that can be used for practice.
    Designed to simulate the actual interview experience.
    """

    scenario_title: str = Field(
        ..., description="Title of this mock interview scenario"
    )
    stage: str = Field(..., description="Which interview stage this simulates")
    duration: str = Field(..., description="Duration of this mock interview")
    opening: str = Field(
        ..., description="How the interviewer typically opens this stage (exact script)"
    )
    questions_sequence: list[str] = Field(
        ..., description="Questions in the order they're typically asked"
    )
    expected_flow: str = Field(
        ..., description="Narrative description of how the interview typically flows"
    )
    closing: str = Field(
        ..., description="How the interviewer typically closes and what happens next"
    )
    time_for_candidate_questions: bool = Field(
        ..., description="Whether candidates get to ask questions at the end"
    )
    good_questions_to_ask: list[str] = Field(
        default_factory=list,
        description="Smart questions candidates should ask the interviewer",
    )


class InterviewInsights(BaseModel):
    """Deep insights about the interview and what to expect."""

    common_questions: list[InterviewQuestion] = Field(
        default_factory=list,
        description="Commonly asked interview questions at this company",
    )
    coding_problems: list[CodingProblem] = Field(
        default_factory=list,
        description="Specific coding problems asked at this company",
    )
    system_design_questions: list[SystemDesignQuestion] = Field(
        default_factory=list,
        description="System design questions asked at this company",
    )
    mock_scenarios: list[MockInterviewScenario] = Field(
        default_factory=list,
        description="Complete mock interview scenarios for practice",
    )
    interview_process: InterviewProcess = Field(
        ..., description="Structure and flow of the interview process"
    )
    technical_requirements: Optional[TechnicalRequirements] = Field(
        None, description="Technical skills and requirements (if applicable)"
    )
    what_they_look_for: list[str] = Field(
        default_factory=list,
        description="Key qualities and traits the company values in candidates",
    )
    red_flags_to_avoid: list[str] = Field(
        default_factory=list,
        description="Things to avoid saying or doing in the interview",
    )
    salary_range: Optional[str] = Field(
        None, description="Expected salary range if available"
    )
    company_values_in_interviews: list[str] = Field(
        default_factory=list,
        description="How company values show up in interview evaluation (e.g., 'Bias for Action' at Amazon)",
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
        ..., description="General company information"
    )
    interview_insights: InterviewInsights = Field(
        ..., description="Interview preparation materials and insights"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="URLs of sources used to compile this information",
    )
    session_id: str = Field(..., description="Yellowcake session ID for tracking")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the scraping process",
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
        ..., description="Current status of the scraping operation"
    )
    message: str = Field(..., description="Human-readable status message")
    progress_percent: int | None = Field(
        default=None, ge=0, le=100, description="Progress percentage if available"
    )
    session_id: str | None = Field(default=None, description="Yellowcake session ID")
    data: CompanyInterviewDataResponse | None = Field(
        default=None, description="Complete data (only present when status='complete')"
    )
