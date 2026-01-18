"""
Service layer using LangChain + LangGraph pipeline.
Orchestrates parallel scraping and agentic analysis.
"""

from __future__ import annotations
import json
import asyncio
from typing import AsyncGenerator, Any, TypedDict, List, Optional

from langgraph.graph import StateGraph, END
from .config import settings
from .models import (
    CompanySearchRequest,
    CompanyInterviewDataResponse,
    CompanyOverview,
    InterviewInsights,
    InterviewProcess,
    InterviewStage,
    InterviewQuestion,
    TechnicalRequirements,
    CodingProblem,
    SystemDesignQuestion,
    MockInterviewScenario,
    ScrapingProgressUpdate,
)
from .cache import get_cache
from .leetcode_scraper import create_leetcode_scraper
from .prompt_optimizer import create_prompt_optimizer
from .scraper_engine import ScraperEngine
from .tpm_limiter import tpm_limiter

from pydantic import SecretStr

# Import agents
from .agents.company_analyst import run_company_analyst
from .agents.interview_architect import run_interview_architect
from .agents.technical_specialist import run_technical_specialist
from .agents.question_strategist import run_question_strategist


# LangGraph State
class InterviewPrepState(TypedDict):
    company_name: str
    position: str
    job_url: str | None
    raw_scraped_data: list[dict[str, Any]]
    session_ids: list[str]

    # Results from agents
    company_overview: dict[str, Any] | None
    technical_requirements: dict[str, Any] | None
    interview_process: dict[str, Any] | None
    common_questions: list[dict[str, Any]]
    coding_problems: list[dict[str, Any]]
    system_design: list[dict[str, Any]]
    mock_scenarios: list[dict[str, Any]]
    what_they_look_for: list[str]
    red_flags_to_avoid: list[str]
    company_values: list[str]
    salary_range: str | None

    final_response: CompanyInterviewDataResponse | None
    error: str | None


class ScraperService:
    def __init__(self, session_id: Optional[str] = None, attempt: int = 0) -> None:
        self.session_id = session_id
        model = settings.llm_model
        api_key = settings.get_llm_api_key(session_id, attempt)
        print(
            f"🚀 Initializing ScraperService (Model: {model}, Session: {session_id}, Attempt: {attempt})"
        )

        # Initialize LLM
        if "llama" in model.lower() or "mixtral" in model.lower():
            from langchain_groq import ChatGroq

            self.llm = ChatGroq(
                model=model, temperature=0.1, api_key=SecretStr(api_key)
            )
        else:
            from langchain_openai import ChatOpenAI

            self.llm = ChatOpenAI(
                model=model,
                temperature=0.1,
                api_key=SecretStr(api_key),
                base_url=settings.llm_api_base or "https://api.moonshot.cn/v1"
                if "moonshot" in model.lower()
                else None,
            )

        self.cache = get_cache()
        self.leetcode_scraper = create_leetcode_scraper()
        self.prompt_optimizer = create_prompt_optimizer()
        self.scraper_engine = ScraperEngine(self.leetcode_scraper)

        # Build LangGraph workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> Any:
        workflow = StateGraph(InterviewPrepState)
        workflow.add_node("scrape", self._scrape_node)
        workflow.add_node("leetcode", self._leetcode_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("structure", self._structure_node)

        workflow.set_entry_point("scrape")
        workflow.add_edge("scrape", "leetcode")
        workflow.add_edge("leetcode", "analyze")
        workflow.add_edge("analyze", "structure")
        workflow.add_edge("structure", END)
        return workflow.compile()

    # --- LangGraph Nodes ---

    async def _scrape_node(self, state: InterviewPrepState) -> dict[str, Any]:
        """Scrape raw data from web sources in parallel."""
        print(f"🔍 [SCRAPE] Starting for {state['company_name']}...")
        company = state["company_name"]
        job_url = state["job_url"]

        tasks = []
        if job_url:
            tasks.append(self._get_job_data(company, job_url))
        tasks.append(self._get_glassdoor_data(company))
        tasks.append(self._get_company_info_data(company))

        results = await asyncio.gather(*tasks)
        return {"raw_scraped_data": [r for r in results if r]}

    async def _leetcode_node(self, state: InterviewPrepState) -> dict[str, Any]:
        """Fetch and enrich LeetCode problems."""
        print(f"💻 [LEETCODE] Fetching for {state['company_name']}...")
        import random

        try:
            problems = await self.leetcode_scraper.get_company_problems(
                state["company_name"], limit=40
            )
            if problems:
                all_enriched = []
                rem = []
                for p in problems:
                    key = str(p.get("leetcode_number") or p.get("title") or "unknown")
                    cached = self.cache.get_scraped_data(
                        "leetcode", "problem_details", key
                    )
                    if cached:
                        all_enriched.append({**p, **cached})
                    else:
                        rem.append(p)

                # Immediate enrichment for 5 random problems
                if rem and len(all_enriched) < 5:
                    targets = random.sample(rem, min(len(rem), 5))
                    newly = await self.leetcode_scraper.enrich_with_details(
                        targets, max_details=len(targets)
                    )
                    all_enriched.extend(newly)

                new_raw = list(state.get("raw_scraped_data", []))
                new_raw.append(
                    {
                        "source_name": "LeetCode Problems",
                        "data": {"problems": all_enriched},
                    }
                )
                return {"raw_scraped_data": new_raw}
        except Exception as e:
            print(f"❌ [LEETCODE] Error: {e}")
        return {}

    async def _analyze_node(self, state: InterviewPrepState) -> dict[str, Any]:
        """Launch all specialized agents in parallel (Promise.all style)."""
        print("\n" + "🤖" * 5 + " [ANALYSIS] Parallel Agent Execution " + "🤖" * 5)

        tasks = [
            run_company_analyst(state, self.llm, self.prompt_optimizer),
            run_interview_architect(state, self.llm, self.prompt_optimizer),
            run_technical_specialist(state, self.llm, self.prompt_optimizer),
            run_question_strategist(state, self.llm, self.prompt_optimizer),
        ]

        results = await asyncio.gather(*tasks)
        updates = {}
        for res in results:
            if res:
                updates.update(res)

        return updates

    def _structure_node(self, state: InterviewPrepState) -> dict[str, Any]:
        """Aggregate all agent outputs into the final Pydantic contract."""
        print("📦 [STRUCTURE] Final aggregation...")

        co = state.get("company_overview") or {}
        tr = state.get("technical_requirements") or {}
        ip = state.get("interview_process") or {}

        # Build models with safety defaults
        overview = CompanyOverview(
            name=co.get("name") or state["company_name"],
            industry=co.get("industry"),
            size=co.get("size"),
            headquarters=co.get("headquarters"),
            mission=co.get("mission"),
            culture=co.get("culture"),
            recent_news=co.get("recent_news") or [],
        )
        tech = TechnicalRequirements(
            programming_languages=tr.get("programming_languages") or [],
            frameworks_tools=tr.get("frameworks_tools") or [],
            concepts=tr.get("concepts") or [],
            experience_level=tr.get("experience_level"),
            must_have_skills=tr.get("must_have_skills") or [],
            nice_to_have_skills=tr.get("nice_to_have_skills") or [],
            domain_knowledge=tr.get("domain_knowledge") or [],
        )
        stages = [
            InterviewStage(**s)
            for s in ip.get("stages", [])
            if isinstance(s, dict) and s.get("stage_name")
        ]
        process = InterviewProcess(
            stages=stages,
            total_duration=ip.get("total_duration"),
            preparation_tips=ip.get("preparation_tips") or [],
        )

        # Construct final response
        response = CompanyInterviewDataResponse(
            success=True,
            company_overview=overview,
            interview_insights=InterviewInsights(
                common_questions=[
                    InterviewQuestion(**q)
                    for q in state.get("common_questions", [])
                    if isinstance(q, dict) and q.get("question")
                ],
                coding_problems=[
                    CodingProblem(**p)
                    for p in state.get("coding_problems", [])
                    if isinstance(p, dict) and p.get("title")
                ],
                system_design_questions=[
                    SystemDesignQuestion(**sd)
                    for sd in state.get("system_design", [])
                    if isinstance(sd, dict) and sd.get("question")
                ],
                mock_scenarios=[
                    MockInterviewScenario(**m)
                    for m in state.get("mock_scenarios", [])
                    if isinstance(m, dict) and m.get("scenario_title")
                ],
                interview_process=process,
                technical_requirements=tech,
                what_they_look_for=state.get("what_they_look_for") or [],
                red_flags_to_avoid=state.get("red_flags_to_avoid") or [],
                salary_range=state.get("salary_range"),
                company_values_in_interviews=state.get("company_values") or [],
            ),
            sources=["Job Posting", "Glassdoor", "Company Website", "LeetCode"],
            session_id=state["session_ids"][0] if state["session_ids"] else "direct",
            metadata={"llm_model": settings.llm_model},
        )

        # Merge background data
        self._merge_background_problems(response, state.get("raw_scraped_data", []))
        return {"final_response": response}

    # --- Helper Methods ---

    async def _get_job_data(self, company: str, url: str):
        cached = self.cache.get_scraped_data(company, "job_posting", str(url))
        if cached:
            return {"source_name": "Job Posting", "data": cached}
        data = await self.scraper_engine.scrape_job_posting(url)
        if data:
            self.cache.set_scraped_data(company, "job_posting", data, str(url))
        return {"source_name": "Job Posting", "data": data} if data else None

    async def _get_glassdoor_data(self, company: str):
        cached = self.cache.get_scraped_data(company, "glassdoor_interviews")
        if cached:
            return {"source_name": "Glassdoor Interviews", "data": cached}
        data = await self.scraper_engine.scrape_glassdoor_interviews(company)
        if data:
            self.cache.set_scraped_data(company, "glassdoor_interviews", data)
        return {"source_name": "Glassdoor Interviews", "data": data} if data else None

    async def _get_company_info_data(self, company: str):
        cached = self.cache.get_scraped_data(company, "company_info")
        if cached:
            return {"source_name": "Company Info", "data": cached}
        data = await self.scraper_engine.scrape_company_info(company)
        if data:
            self.cache.set_scraped_data(company, "company_info", data)
        return {"source_name": "Company Info", "data": data} if data else None

    def _merge_background_problems(
        self, response: CompanyInterviewDataResponse, raw: list[dict[str, Any]]
    ):
        existing_ids = {
            p.leetcode_number
            for p in response.interview_insights.coding_problems
            if p.leetcode_number
        }
        for item in raw:
            if item.get("source_name") == "LeetCode Problems":
                for p in item.get("data", {}).get("problems", []):
                    if p.get("leetcode_number") not in existing_ids:
                        try:
                            response.interview_insights.coding_problems.append(
                                CodingProblem(
                                    title=p.get("title", "Unknown"),
                                    difficulty=p.get("difficulty", "medium")
                                    if p.get("difficulty") in ["easy", "medium", "hard"]
                                    else "medium",
                                    problem_statement=p.get("problem_statement", ""),
                                    leetcode_number=p.get("leetcode_number"),
                                    leetcode_url=p.get("url"),
                                    optimal_time_complexity=p.get(
                                        "optimal_time_complexity"
                                    ),
                                    optimal_space_complexity=p.get(
                                        "optimal_space_complexity"
                                    ),
                                    example_input=p.get("example_input") or "",
                                    example_output=p.get("example_output") or "",
                                    frequency="common",
                                    topics=[],
                                    approach_hints=[],
                                    constraints=[],
                                    company_specific_notes="Recovered from background cache.",
                                )
                            )
                        except:
                            pass

    # --- Public API ---

    async def scrape_company_data(
        self, request: CompanySearchRequest
    ) -> CompanyInterviewDataResponse:
        initial_state = self._get_initial_state(request)
        final_state = await self.workflow.ainvoke(initial_state)
        return final_state["final_response"]

    async def scrape_company_data_stream(
        self, request: CompanySearchRequest
    ) -> AsyncGenerator[ScrapingProgressUpdate, None]:
        yield ScrapingProgressUpdate(
            status="started",
            message=f"🔍 Starting research on {request.company_name}...",
            progress_percent=0,
        )
        initial_state = self._get_initial_state(request)
        final_state = await self.workflow.ainvoke(initial_state)
        yield ScrapingProgressUpdate(
            status="complete",
            message="🎉 Analysis complete!",
            progress_percent=100,
            data=final_state.get("final_response"),
        )

    def _get_initial_state(self, request: CompanySearchRequest) -> InterviewPrepState:
        return {
            "company_name": request.company_name,
            "position": request.position or "SDE",
            "job_url": str(request.job_posting_url)
            if request.job_posting_url
            else None,
            "raw_scraped_data": [],
            "session_ids": ["direct"],
            "company_overview": None,
            "technical_requirements": None,
            "interview_process": None,
            "common_questions": [],
            "coding_problems": [],
            "system_design": [],
            "mock_scenarios": [],
            "what_they_look_for": [],
            "red_flags_to_avoid": [],
            "company_values": [],
            "salary_range": None,
            "final_response": None,
            "error": None,
        }

    async def background_enrichment(self, company_name: str):
        """Update cache in background sequentially to respect TPM."""
        try:
            problems = await self.leetcode_scraper.get_company_problems(
                company_name, limit=50
            )
            if problems:
                # Use sequential processing for background to avoid TPM spikes
                await self.leetcode_scraper.enrich_with_details(
                    problems, max_details=50, sequential=True
                )
        except Exception as e:
            print(f"⚠️ [BACKGROUND] Enrichment failed for {company_name}: {e}")
