"""
Service layer using LangChain + LangGraph pipeline.
Multi-stage workflow: Custom scraping → LeetCode scraping → Groq/Llama analysis → Structured output
Includes caching to prevent duplicate scraping and LLM calls.
"""

from __future__ import annotations
import json
import httpx
from typing import AsyncGenerator, Any, TypedDict
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END  # type: ignore[import-untyped]
from config import settings
from models import (
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
from cache import get_cache
from leetcode_scraper import create_leetcode_scraper
from prompt_optimizer import create_prompt_optimizer


# LangGraph State Definition
class InterviewPrepState(TypedDict):
    """State passed through the LangGraph workflow."""

    company_name: str
    position: str
    job_url: str | None
    raw_scraped_data: list[dict[str, Any]]
    session_ids: list[str]
    llm_analysis: dict[str, Any] | None
    final_response: CompanyInterviewDataResponse | None
    error: str | None
    # For self-healing workflow
    messages: list[BaseMessage]
    retry_count: int


class ScraperService:
    """
    LangGraph-based pipeline for interview preparation:

    Node 1: Scrape with custom scraping engine
    Node 2: Scrape LeetCode problems (modular, swappable with Yellowcake)
    Node 3: Analyze with Groq (via LangChain) - with caching
    Node 4: Structure response
    """

    def __init__(self) -> None:
        # Set GROQ_API_KEY in environment for LangChain
        import os

        os.environ["GROQ_API_KEY"] = settings.groq_api_key

        # Initialize Groq with LangChain
        self.llm = ChatGroq(model=settings.groq_model, temperature=0.3)

        # Initialize cache, LeetCode scraper, and prompt optimizer
        self.cache = get_cache()
        self.leetcode_scraper = create_leetcode_scraper()
        self.prompt_optimizer = create_prompt_optimizer()

        # Build LangGraph workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> Any:
        """
        Build the LangGraph workflow for interview prep pipeline.

        Workflow:
        START → scrape_node → leetcode_node → analyze_node ↻ (retry on error) → structure_node → END
        """
        workflow = StateGraph(InterviewPrepState)

        # Add nodes
        workflow.add_node("scrape", self._scrape_node)
        workflow.add_node("leetcode", self._leetcode_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("structure", self._structure_node)

        # Define edges
        workflow.set_entry_point("scrape")
        workflow.add_edge("scrape", "leetcode")
        workflow.add_edge("leetcode", "analyze")

        # Add conditional edge for self-healing
        workflow.add_conditional_edges(
            "analyze", self._should_retry, {"retry": "analyze", "continue": "structure"}
        )

        workflow.add_edge("structure", END)

        return workflow.compile()

    def _should_retry(self, state: InterviewPrepState) -> str:
        """Determine if we should retry the analysis step."""
        if state.get("error") and state.get("retry_count", 0) < 3:
            print(
                f"🔄 Retrying analysis... (Attempt {state.get('retry_count', 0) + 1}/3)"
            )
            return "retry"
        return "continue"

    async def _analyze_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """
        LangGraph Node 3: Analyze raw data with Groq/Llama using LangChain.
        Enhanced with caching, interview-reconstruction-level prompting, AND self-healing.
        """
        print(f"🤖 Analyzing with Groq ({settings.groq_model})...")

        # Initialize retry count if not present
        if "retry_count" not in state:
            state["retry_count"] = 0

        # Initialize messages if not present (First attempt)
        if "messages" not in state or not state["messages"]:
            # Combine raw text
            raw_text_parts: list[str] = []
            for item in state["raw_scraped_data"]:
                raw_text_parts.append(f"\n=== {item['source_name']} ===\n")
                raw_text_parts.append(json.dumps(item["data"], indent=2))

            combined_raw_text = "\n".join(raw_text_parts)[:25000]

            # Check LLM cache first (only on first attempt)
            cache_key_data = (
                f"{state['company_name']}|{state['position']}|{combined_raw_text[:500]}"
            )
            if state["retry_count"] == 0:
                cached_analysis = self.cache.get_llm_response(
                    prompt=cache_key_data, model=settings.groq_model
                )

                if cached_analysis:
                    print("✅ LLM Cache hit - using cached analysis")
                    state["llm_analysis"] = cached_analysis
                    state["error"] = None
                    return state

            # Use static optimized prompt
            print("🤖 Using static optimized interview reconstruction prompt...")
            formatted_messages = self.prompt_optimizer.get_static_prompt(
                company_name=state["company_name"],
                position=state["position"],
                scraped_data=combined_raw_text,
            )
            state["messages"] = formatted_messages

        try:
            # Use LangChain to call Groq
            # Pass the accumulated messages (history) to the LLM
            response = await self.llm.ainvoke(state["messages"])
            content = response.content

            # Add the AI's response to history
            state["messages"].append(AIMessage(content=str(content)))

            if not content or not isinstance(content, str):
                print(f"⚠️ Empty or invalid response from LLM: {content}")
                state["error"] = "Empty response from LLM"
                state["retry_count"] += 1
                return state

            # Robust JSON extraction
            try:
                # Find first '{' and last '}'
                start_idx = content.find("{")
                end_idx = content.rfind("}")

                if start_idx != -1 and end_idx != -1:
                    json_str = content[start_idx : end_idx + 1]
                    try:
                        analysis = json.loads(json_str)
                    except json.JSONDecodeError as je:
                        print(f"❌ [JSON ERROR] Invalid JSON structure from LLM.")
                        print(f"--- FAILED JSON START ---")
                        print(json_str[:1000] + "...")
                        print(f"--- FAILED JSON END ---")
                        raise je

                    state["llm_analysis"] = analysis
                    state["error"] = None  # Clear error on success

                    print("✅ Analysis successful")
                else:
                    error_msg = f"❌ [LLM FAILURE] No JSON object found in LLM response. Content: {content[:500]}..."
                    print(error_msg)
                    state["error"] = error_msg
                    state["retry_count"] += 1
                    # Add error feedback to messages
                    state["messages"].append(HumanMessage(content=error_msg))

            except json.JSONDecodeError as e:
                error_msg = f"JSON Parse Error: {str(e)}. Please fix the JSON format. Ensure all strings are quoted and braces are balanced."
                print(f"❌ {error_msg}")
                state["error"] = error_msg
                state["retry_count"] += 1
                # Add error feedback to messages
                state["messages"].append(HumanMessage(content=error_msg))

        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            state["error"] = str(e)
            state["retry_count"] += 1

        return state

    async def _scrape_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """
        LangGraph Node 1: Scrape raw data using custom scraping engine.
        """
        print(f"🔍 Scraping data for {state['company_name']}...")

        company = state["company_name"]
        job_url = state["job_url"]

        all_raw_data: list[dict[str, Any]] = []

        # 1. Scrape job posting if provided (with caching)
        if job_url:
            try:
                # Check cache first
                cached_job = self.cache.get_scraped_data(
                    company=company, source="job_posting", url=str(job_url)
                )
                if cached_job:
                    print(f"✅ Cache hit for job posting: {job_url}")
                    all_raw_data.append(
                        {"source_name": "Job Posting", "data": cached_job}
                    )
                else:
                    job_data = await self._scrape_job_posting(job_url)
                    if job_data:
                        # Cache the result
                        self.cache.set_scraped_data(
                            company=company,
                            source="job_posting",
                            data=job_data,
                            url=str(job_url),
                        )
                        all_raw_data.append(
                            {"source_name": "Job Posting", "data": job_data}
                        )
            except Exception as e:
                print(f"Warning: Error scraping job posting: {e}")

        # 2. Scrape Glassdoor interview reviews (with caching)
        try:
            cached_glassdoor = self.cache.get_scraped_data(
                company=company, source="glassdoor_interviews"
            )
            if cached_glassdoor:
                print(f"✅ Cache hit for Glassdoor interviews: {company}")
                all_raw_data.append(
                    {"source_name": "Glassdoor Interviews", "data": cached_glassdoor}
                )
            else:
                glassdoor_data = await self._scrape_glassdoor_interviews(company)
                if glassdoor_data:
                    # Cache the result
                    self.cache.set_scraped_data(
                        company=company,
                        source="glassdoor_interviews",
                        data=glassdoor_data,
                    )
                    all_raw_data.append(
                        {"source_name": "Glassdoor Interviews", "data": glassdoor_data}
                    )
        except Exception as e:
            print(f"Warning: Error scraping Glassdoor: {e}")

        # 3. Scrape company info from their careers page (with caching)
        try:
            cached_company = self.cache.get_scraped_data(
                company=company, source="company_info"
            )
            if cached_company:
                print(f"✅ Cache hit for company info: {company}")
                all_raw_data.append(
                    {"source_name": "Company Info", "data": cached_company}
                )
            else:
                company_data = await self._scrape_company_info(company)
                if company_data:
                    # Cache the result
                    self.cache.set_scraped_data(
                        company=company, source="company_info", data=company_data
                    )
                    all_raw_data.append(
                        {"source_name": "Company Info", "data": company_data}
                    )
        except Exception as e:
            print(f"Warning: Error scraping company info: {e}")

        # Update state
        state["raw_scraped_data"] = all_raw_data
        state["session_ids"] = ["direct-scrape"]  # No session IDs needed

        return state

    async def _leetcode_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """
        LangGraph Node 2: Scrape company-specific LeetCode problems.
        Optimized for responsiveness: scrapes a few immediately, others handled via cache later.
        """
        print(f"💻 Fetching LeetCode problems for {state['company_name']}...")
        import random

        try:
            # Get company-specific problems (with caching built-in)
            problems = await self.leetcode_scraper.get_company_problems(
                company_name=state["company_name"],
                limit=30,  # Get a decent list
            )

            if problems:
                # 1. Immediate Enrichment (Fast path)
                # Pick 3 random problems to enrich immediately for the response
                num_immediate = min(3, len(problems))
                immediate_targets = random.sample(problems, num_immediate)

                print(
                    f"⚡ [FAST PATH] Enriching {num_immediate} random problems immediately..."
                )
                enriched = await self.leetcode_scraper.enrich_with_details(
                    immediate_targets, max_details=num_immediate
                )

                # 2. Background Enrichment (Slow path)
                # We'll return the 3 now, and the rest can be enriched in the background
                # Note: In a real production system, we'd trigger a background worker here.
                # For this setup, we'll use FastAPI BackgroundTasks in the controller.

                # Add to scraped data
                state["raw_scraped_data"].append(
                    {
                        "source_name": "LeetCode Problems",
                        "data": {
                            "company": state["company_name"],
                            "problems": enriched,
                            "total_count": len(problems),
                            "note": f"Enriched {len(enriched)} problems immediately. Full set being processed in background.",
                        },
                    }
                )

                print(
                    f"✅ Found {len(problems)} LeetCode problems, enriched {len(enriched)} immediately."
                )
            else:
                print(f"⚠️ No LeetCode problems found for {state['company_name']}")

        except Exception as e:
            print(f"Warning: Error fetching LeetCode problems: {e}")

        return state

    async def background_enrichment(self, company_name: str):
        """
        Background task to fully enrich all LeetCode problems for a company.
        This updates the cache so future requests are instant.
        """
        print(f"🕵️ [BACKGROUND] Starting full enrichment for {company_name}...")
        try:
            problems = await self.leetcode_scraper.get_company_problems(
                company_name, limit=50
            )
            if problems:
                # This will populate the cache for each individual problem
                await self.leetcode_scraper.enrich_with_details(
                    problems, max_details=50
                )
                print(f"✅ [BACKGROUND] Full enrichment complete for {company_name}")
        except Exception as e:
            print(f"❌ [BACKGROUND] Error: {e}")

    def _structure_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """
        LangGraph Node 3: Convert LLM output to Pydantic models.
        """
        print("📦 Structuring response...")

        if state.get("error") or not state.get("llm_analysis"):
            # Create fallback response
            state["final_response"] = self._create_fallback_response(
                state["company_name"], state["session_ids"]
            )
            return state

        try:
            analysis = state["llm_analysis"]
            if analysis is None:
                raise ValueError("LLM analysis is None")

            state["final_response"] = self._convert_llm_to_response(
                state["company_name"], analysis, state["session_ids"]
            )
        except Exception as e:
            print(f"Error structuring response: {e}")
            state["final_response"] = self._create_fallback_response(
                state["company_name"], state["session_ids"]
            )

        return state

    async def scrape_company_data(
        self, request: CompanySearchRequest
    ) -> CompanyInterviewDataResponse:
        """
        Execute the LangGraph workflow to scrape and analyze company data.

        Workflow: scrape → analyze → structure

        Args:
            request: Company search request

        Returns:
            Complete interview preparation response
        """
        # Initialize state
        initial_state: InterviewPrepState = {
            "company_name": request.company_name,
            "position": request.position or "general position",
            "job_url": str(request.job_posting_url)
            if request.job_posting_url
            else None,
            "raw_scraped_data": [],
            "session_ids": [],
            "llm_analysis": None,
            "final_response": None,
            "error": None,
            "messages": [],
            "retry_count": 0,
        }

        # Run the workflow
        try:
            print("🔄 Starting LangGraph execution...")
            final_state = await self.workflow.ainvoke(initial_state)
            print("✅ LangGraph execution completed")
        except Exception as e:
            print(f"❌ LangGraph Execution Failed: {e}")
            import traceback

            traceback.print_exc()
            raise e

        # Return the final response
        if final_state["final_response"]:
            return final_state["final_response"]
        else:
            # Fallback
            return self._create_fallback_response(
                request.company_name, final_state.get("session_ids", [])
            )

    def _convert_llm_to_response(
        self, company_name: str, llm_analysis: dict[str, Any], session_ids: list[str]
    ) -> CompanyInterviewDataResponse:
        """Convert LLM JSON output to our typed Pydantic response."""

        # Parse company overview
        overview_data = llm_analysis.get("company_overview", {})
        recent_news = overview_data.get("recent_news", [])
        # Handle if LLM returns string instead of list
        if isinstance(recent_news, str):
            recent_news = [recent_news] if recent_news else []

        company_overview = CompanyOverview(
            name=overview_data.get("name", company_name),
            industry=overview_data.get("industry"),
            size=overview_data.get("size"),
            headquarters=overview_data.get("headquarters"),
            mission=overview_data.get("mission"),
            culture=overview_data.get("culture"),
            recent_news=recent_news,
        )

        # Parse interview questions (with enhanced fields)
        questions: list[InterviewQuestion] = []
        raw_qs = llm_analysis.get("interview_questions", [])
        for idx, q in enumerate(raw_qs[:30]):
            try:
                # Self-healing for list fields
                processed_q = q.copy() if isinstance(q, dict) else {}
                for list_field in [
                    "key_points_to_cover",
                    "follow_up_questions",
                    "red_flags",
                ]:
                    if list_field in processed_q and isinstance(
                        processed_q[list_field], str
                    ):
                        print(
                            f"🔧 [HEALING] Converting string field '{list_field}' to list for question {idx}"
                        )
                        processed_q[list_field] = [processed_q[list_field]]

                questions.append(
                    InterviewQuestion(
                        question=processed_q.get("question", ""),
                        category=processed_q.get("category", "behavioral"),
                        difficulty=processed_q.get("difficulty"),
                        tips=processed_q.get("tips"),
                        sample_answer=processed_q.get("sample_answer"),
                        key_points_to_cover=processed_q.get("key_points_to_cover")
                        or [],
                        follow_up_questions=processed_q.get("follow_up_questions")
                        or [],
                        red_flags=processed_q.get("red_flags") or [],
                        company_specific_context=processed_q.get(
                            "company_specific_context"
                        ),
                    )
                )
            except Exception as e:
                print(f"🔥 [QUESTION PARSE FAILURE] Index: {idx}")
                print(f"❌ Error Detail: {str(e)}")
                print(f"📦 Raw Input Data: {json.dumps(q, indent=2)}")
                continue

        # Parse coding problems
        coding_problems: list[CodingProblem] = []
        raw_probs = llm_analysis.get("coding_problems", [])
        for idx, prob in enumerate(raw_probs):
            try:
                # Pre-processing/Healing for common LLM structure errors
                # If constraints/hints are strings instead of lists, convert them
                processed_prob = prob.copy() if isinstance(prob, dict) else {}

                for field in ["constraints", "approach_hints", "topics"]:
                    if field in processed_prob and isinstance(
                        processed_prob[field], str
                    ):
                        print(
                            f"🔧 [HEALING] Converting string field '{field}' to list for coding problem {idx}"
                        )
                        processed_prob[field] = [processed_prob[field]]

                coding_problems.append(
                    CodingProblem(
                        title=processed_prob.get("title", ""),
                        difficulty=processed_prob.get("difficulty", "medium"),
                        problem_statement=processed_prob.get("problem_statement", ""),
                        example_input=processed_prob.get("example_input"),
                        example_output=processed_prob.get("example_output"),
                        constraints=processed_prob.get("constraints") or [],
                        leetcode_number=processed_prob.get("leetcode_number"),
                        leetcode_url=processed_prob.get("leetcode_url"),
                        topics=processed_prob.get("topics") or [],
                        approach_hints=processed_prob.get("approach_hints") or [],
                        optimal_time_complexity=processed_prob.get(
                            "optimal_time_complexity"
                        ),
                        optimal_space_complexity=processed_prob.get(
                            "optimal_space_complexity"
                        ),
                        frequency=processed_prob.get("frequency"),
                        company_specific_notes=processed_prob.get(
                            "company_specific_notes"
                        ),
                    )
                )
            except Exception as e:
                print(f"🔥 [CODING PROBLEM PARSE FAILURE] Index: {idx}")
                print(f"❌ Error Detail: {str(e)}")
                print(f"📦 Raw Input Data: {json.dumps(prob, indent=2)}")
                continue

        # Parse system design questions
        system_design: list[SystemDesignQuestion] = []
        for sd in llm_analysis.get("system_design_questions", [])[:10]:
            try:
                system_design.append(
                    SystemDesignQuestion(
                        question=sd.get("question", ""),
                        scope=sd.get("scope", ""),
                        key_components=sd.get("key_components", []),
                        evaluation_criteria=sd.get("evaluation_criteria", []),
                        common_approaches=sd.get("common_approaches", []),
                        follow_up_topics=sd.get("follow_up_topics", []),
                        time_allocation=sd.get("time_allocation"),
                    )
                )
            except Exception as e:
                print(f"Warning: Failed to parse system design question: {e}")
                continue

        # Parse mock scenarios
        mock_scenarios: list[MockInterviewScenario] = []
        for mock in llm_analysis.get("mock_scenarios", [])[:5]:
            try:
                mock_scenarios.append(
                    MockInterviewScenario(
                        scenario_title=mock.get("scenario_title", ""),
                        stage=mock.get("stage", ""),
                        duration=mock.get("duration", ""),
                        opening=mock.get("opening", ""),
                        questions_sequence=mock.get("questions_sequence", []),
                        expected_flow=mock.get("expected_flow", ""),
                        closing=mock.get("closing", ""),
                        time_for_candidate_questions=mock.get(
                            "time_for_candidate_questions", True
                        ),
                        good_questions_to_ask=mock.get("good_questions_to_ask", []),
                    )
                )
            except Exception as e:
                print(f"Warning: Failed to parse mock scenario: {e}")
                continue

        # Parse interview stages (with enhanced fields)
        stages: list[InterviewStage] = []
        process_data = llm_analysis.get("interview_process", {})
        raw_stages = process_data.get("stages", [])

        for idx, stage in enumerate(raw_stages):
            try:
                if isinstance(stage, str):
                    print(
                        f"⚠️ [PARSING ERROR] Stage {idx} is a string ('{stage[:50]}...'), expected an object. Attempting recovery."
                    )
                    stages.append(
                        InterviewStage(
                            stage_name=stage,
                            description="Details not provided in structured format.",
                            duration=None,
                            format=None,
                            interviewers=None,
                            focus_areas=[],
                            sample_questions=[],
                            success_criteria=[],
                            preparation_strategy=None,
                        )
                    )
                    continue

                if not isinstance(stage, dict):
                    print(
                        f"❌ [PARSING FAILURE] Stage {idx} is type {type(stage)}, cannot parse. Value: {stage}"
                    )
                    continue

                # Validate required field stage_name
                name = stage.get("name", stage.get("stage_name"))
                if not name:
                    print(
                        f"⚠️ [PARSING ERROR] Stage {idx} missing name/stage_name. Raw data: {stage}"
                    )
                    name = f"Unknown Stage {idx + 1}"

                stages.append(
                    InterviewStage(
                        stage_name=name,
                        description=stage.get("description"),
                        duration=stage.get("duration"),
                        format=stage.get("format"),
                        interviewers=stage.get("interviewers"),
                        focus_areas=stage.get("focus_areas", []),
                        sample_questions=stage.get("sample_questions", []),
                        success_criteria=stage.get("success_criteria", []),
                        preparation_strategy=stage.get("preparation_strategy"),
                    )
                )
            except Exception as e:
                print(
                    f"🔥 [CRITICAL PARSE ERROR] Failed to process stage {idx}: {str(e)}"
                )
                import traceback

                traceback.print_exc()
                continue
            except Exception as e:
                print(f"Warning: Failed to parse stage: {e}")
                continue

        interview_process = InterviewProcess(
            stages=stages,
            total_duration=process_data.get("total_duration"),
            preparation_tips=process_data.get("preparation_tips", []),
        )

        # Parse technical requirements (with enhanced fields)
        tech_data = llm_analysis.get("technical_requirements")
        technical_requirements = None
        if tech_data:
            technical_requirements = TechnicalRequirements(
                programming_languages=tech_data.get("programming_languages", []),
                frameworks_tools=tech_data.get("frameworks_tools", []),
                concepts=tech_data.get("concepts", []),
                experience_level=tech_data.get("experience_level"),
                must_have_skills=tech_data.get("must_have_skills", []),
                nice_to_have_skills=tech_data.get("nice_to_have_skills", []),
                domain_knowledge=tech_data.get("domain_knowledge", []),
            )

        # Build enhanced insights
        interview_insights = InterviewInsights(
            common_questions=questions,
            coding_problems=coding_problems,
            system_design_questions=system_design,
            mock_scenarios=mock_scenarios,
            interview_process=interview_process,
            technical_requirements=technical_requirements,
            what_they_look_for=llm_analysis.get("what_they_look_for", []),
            red_flags_to_avoid=llm_analysis.get("red_flags_to_avoid", []),
            salary_range=llm_analysis.get("salary_range"),
            company_values_in_interviews=llm_analysis.get(
                "company_values_in_interviews", []
            ),
        )

        return CompanyInterviewDataResponse(
            success=True,
            company_overview=company_overview,
            interview_insights=interview_insights,
            sources=["Job Posting", "Glassdoor", "Company Website"],
            session_id=session_ids[0] if session_ids else "no-session",
            metadata={
                "scrape_sources": ["direct_scraping"],
                "llm_model": settings.groq_model,
                "processing_pipeline": "custom_scrape -> groq_llama_analysis -> langgraph",
            },
        )

    def _create_fallback_response(
        self, company_name: str, session_ids: list[str]
    ) -> CompanyInterviewDataResponse:
        """Create a basic response if LLM analysis fails."""
        return CompanyInterviewDataResponse(
            success=False,
            company_overview=CompanyOverview(
                name=company_name,
                industry=None,
                size=None,
                headquarters=None,
                mission=None,
                culture=None,
                recent_news=[],
            ),
            interview_insights=InterviewInsights(
                common_questions=[],
                interview_process=InterviewProcess(
                    stages=[], total_duration=None, preparation_tips=[]
                ),
                technical_requirements=None,
                what_they_look_for=[],
                red_flags_to_avoid=[],
                salary_range=None,
            ),
            sources=[],
            session_id=session_ids[0] if session_ids else "no-session",
            metadata={"error": "Failed to analyze data"},
        )

    async def scrape_company_data_stream(
        self, request: CompanySearchRequest
    ) -> AsyncGenerator[ScrapingProgressUpdate, None]:
        """
        Stream company data scraping progress via LangGraph workflow.

        Shows progress through: scrape → analyze → structure stages
        """
        yield ScrapingProgressUpdate(
            status="started",
            message=f"🔍 Starting LangGraph pipeline for {request.company_name}",
            progress_percent=0,
        )

        # Initialize state
        initial_state: InterviewPrepState = {
            "company_name": request.company_name,
            "position": request.position or "general position",
            "job_url": str(request.job_posting_url)
            if request.job_posting_url
            else None,
            "raw_scraped_data": [],
            "session_ids": [],
            "llm_analysis": None,
            "final_response": None,
            "error": None,
            "messages": [],
            "retry_count": 0,
        }

        # Execute workflow with progress updates
        try:
            # Stage 1: Scraping
            yield ScrapingProgressUpdate(
                status="in_progress",
                message="📊 Node 1: Scraping job postings, Glassdoor & company info...",
                progress_percent=10,
            )

            final_state = await self.workflow.ainvoke(initial_state)

            yield ScrapingProgressUpdate(
                status="complete",
                message=f"🎉 Pipeline complete for {request.company_name}!",
                progress_percent=100,
                session_id=final_state.get("session_ids", [None])[0],
                data=final_state.get("final_response"),
            )

        except Exception as e:
            yield ScrapingProgressUpdate(
                status="error",
                message=f"❌ Error in pipeline: {str(e)}",
                progress_percent=0,
            )

    async def _scrape_job_posting(self, url: str) -> dict[str, Any] | None:
        """Scrape a job posting URL and extract structured information."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                # Extract text content
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                text = soup.get_text(separator="\n", strip=True)

                # Clean up text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_text = "\n".join(lines)

                # Try to extract structured sections
                sections: dict[str, Any] = {
                    "full_content": clean_text[:15000],  # Increased from 10k
                    "url": url,
                }

                # Look for common section headers
                text_lower = clean_text.lower()
                if "responsibilities" in text_lower or "what you'll do" in text_lower:
                    sections["has_responsibilities"] = True
                if "requirements" in text_lower or "qualifications" in text_lower:
                    sections["has_requirements"] = True
                if "skills" in text_lower or "technical" in text_lower:
                    sections["has_technical_skills"] = True
                if "benefits" in text_lower or "perks" in text_lower:
                    sections["has_benefits"] = True

                return sections
        except Exception as e:
            print(f"Error scraping job posting: {e}")
            return None

    async def _scrape_glassdoor_interviews(self, company: str) -> dict[str, Any] | None:
        """Scrape Glassdoor interview reviews."""
        try:
            # Search for company interviews on Glassdoor
            search_url = f"https://www.glassdoor.com/Interview/{company.replace(' ', '-')}-interview-questions-SRCH_KE0,{len(company)}.htm"

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = await client.get(search_url, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                # Extract interview experiences
                interviews = []

                # Try to find interview sections
                for element in soup.find_all(["div", "article", "section"]):
                    text = element.get_text(separator=" ", strip=True)
                    if len(text) > 100 and any(
                        keyword in text.lower()
                        for keyword in ["interview", "question", "process", "round"]
                    ):
                        interviews.append(text[:1000])

                    if len(interviews) >= 10:  # Limit to 10 interviews
                        break

                if not interviews:
                    # Fallback: get all text
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    return {"content": text[:8000]}

                return {"interviews": interviews, "count": len(interviews)}
        except Exception as e:
            print(f"Error scraping Glassdoor: {e}")
            return None

    async def _scrape_company_info(self, company: str) -> dict[str, Any] | None:
        """Scrape company information from their careers/about page."""
        try:
            # Try to find company careers page
            search_query = f"{company} careers about culture"
            search_url = (
                f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            )

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = await client.get(search_url, headers=headers)

                soup = BeautifulSoup(response.text, "lxml")

                # Extract text from search results
                results = []
                for element in soup.find_all(["div", "span", "p"]):
                    text = element.get_text(separator=" ", strip=True)
                    if len(text) > 50 and company.lower() in text.lower():
                        results.append(text[:500])

                    if len(results) >= 5:
                        break

                return {"company": company, "info": results}
        except Exception as e:
            print(f"Error scraping company info: {e}")
            return None
