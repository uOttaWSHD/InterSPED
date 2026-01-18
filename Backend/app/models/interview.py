from pydantic import BaseModel, Field
from typing import Optional, List


class CodingProblem(BaseModel):
    title: Optional[str] = None
    difficulty: Optional[str] = None
    problem_statement: Optional[str] = None
    example_input: Optional[str] = None
    example_output: Optional[str] = None
    constraints: Optional[list[str]] = None
    leetcode_number: Optional[int] = None
    leetcode_url: Optional[str] = None
    topics: Optional[list[str]] = None
    approach_hints: Optional[list[str]] = None
    optimal_time_complexity: Optional[str] = None
    optimal_space_complexity: Optional[str] = None
    frequency: Optional[str] = None
    company_specific_notes: Optional[str] = None


class CommonQuestion(BaseModel):
    question: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    tips: Optional[str] = None
    sample_answer: Optional[str] = None
    key_points_to_cover: Optional[list[str]] = None
    follow_up_questions: Optional[list[str]] = None
    red_flags: Optional[list[str]] = None
    company_specific_context: Optional[str] = None


class SystemDesignQuestion(BaseModel):
    question: Optional[str] = None
    scope: Optional[str] = None
    key_components: Optional[list[str]] = None
    evaluation_criteria: Optional[list[str]] = None
    common_approaches: Optional[list[str]] = None
    follow_up_topics: Optional[list[str]] = None
    time_allocation: Optional[str] = None


class MockScenario(BaseModel):
    scenario_title: Optional[str] = None
    stage: Optional[str] = None
    duration: Optional[str] = None
    opening: Optional[str] = None
    questions_sequence: Optional[list[str]] = None
    expected_flow: Optional[str] = None
    closing: Optional[str] = None
    time_for_candidate_questions: Optional[bool] = None
    good_questions_to_ask: Optional[list[str]] = None


class InterviewStage(BaseModel):
    stage_name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[str] = None
    format: Optional[str] = None
    interviewers: Optional[str] = None
    focus_areas: Optional[list[str]] = None
    sample_questions: Optional[list[str]] = None
    success_criteria: Optional[list[str]] = None
    preparation_strategy: Optional[str] = None


class InterviewProcess(BaseModel):
    stages: Optional[list[InterviewStage]] = None
    total_duration: Optional[str] = None
    preparation_tips: Optional[list[str]] = None


class TechnicalRequirements(BaseModel):
    programming_languages: Optional[list[str]] = Field(default_factory=list)
    frameworks_tools: Optional[list[str]] = Field(default_factory=list)
    concepts: Optional[list[str]] = Field(default_factory=list)
    experience_level: Optional[str] = None
    must_have_skills: Optional[list[str]] = Field(default_factory=list)
    nice_to_have_skills: Optional[list[str]] = Field(default_factory=list)
    domain_knowledge: Optional[list[str]] = Field(default_factory=list)


class InterviewInsights(BaseModel):
    common_questions: Optional[list[CommonQuestion]] = None
    coding_problems: Optional[list[CodingProblem]] = None
    system_design_questions: Optional[list[SystemDesignQuestion]] = None
    mock_scenarios: Optional[list[MockScenario]] = None
    interview_process: Optional[InterviewProcess] = None
    technical_requirements: Optional[TechnicalRequirements] = None
    what_they_look_for: Optional[list[str]] = None
    red_flags_to_avoid: Optional[list[str]] = None
    salary_range: Optional[str] = None
    company_values_in_interviews: Optional[list[str]] = None


class CompanyOverview(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    headquarters: Optional[str] = None
    mission: Optional[str] = None
    culture: Optional[str] = None
    recent_news: Optional[list[str]] = None


class StartRequest(BaseModel):
    success: bool = True
    company_overview: Optional[CompanyOverview] = None
    interview_insights: Optional[InterviewInsights] = None
    sources: list[str] = []
    session_id: str = ""
    metadata: dict = {}


class RespondRequest(BaseModel):
    session_id: str
    text: str


class SummaryRequest(BaseModel):
    session_id: str


class StartResponse(BaseModel):
    session_id: str
    response: str
    turn: int
    interview_complete: bool


class RespondResponse(BaseModel):
    session_id: str
    response: str
    turn: int
    interview_complete: bool


class SummaryResponse(BaseModel):
    summary: str
    transcript: str


class StatusResponse(BaseModel):
    session_id: str
    turn: int
    max_turns: int
    interview_complete: bool
