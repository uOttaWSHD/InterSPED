"""
Service layer using LangChain + LangGraph pipeline.
Multi-stage workflow: Custom scraping → Groq/Llama analysis → Structured output
"""
from __future__ import annotations
import json
import httpx
from typing import AsyncGenerator, Any, TypedDict
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
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
    ScrapingProgressUpdate
)


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


class ScraperService:
    """
    LangGraph-based pipeline for interview preparation:
    
    Node 1: Scrape with custom scraping engine
    Node 2: Analyze with Groq (via LangChain)
    Node 3: Structure response
    """
    
    def __init__(self) -> None:
        # Set GROQ_API_KEY in environment for LangChain
        import os
        os.environ["GROQ_API_KEY"] = settings.groq_api_key
        
        # Initialize Groq with LangChain
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=0.3
        )
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> Any:  # type: ignore[misc]
        """
        Build the LangGraph workflow for interview prep pipeline.
        
        Workflow:
        START → scrape_node → analyze_node → structure_node → END
        """
        workflow: StateGraph[InterviewPrepState] = StateGraph(InterviewPrepState)  # type: ignore[misc]
        
        # Add nodes
        workflow.add_node("scrape", self._scrape_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("structure", self._structure_node)
        
        # Define edges
        workflow.set_entry_point("scrape")
        workflow.add_edge("scrape", "analyze")
        workflow.add_edge("analyze", "structure")
        workflow.add_edge("structure", END)
        
        return workflow.compile()
    
    async def _scrape_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """
        LangGraph Node 1: Scrape raw data using custom scraping engine.
        """
        print(f"🔍 Scraping data for {state['company_name']}...")
        
        company = state["company_name"]
        job_url = state["job_url"]
        
        all_raw_data: list[dict[str, Any]] = []
        
        # 1. Scrape job posting if provided
        if job_url:
            try:
                job_data = await self._scrape_job_posting(job_url)
                if job_data:
                    all_raw_data.append({
                        "source_name": "Job Posting",
                        "data": job_data
                    })
            except Exception as e:
                print(f"Warning: Error scraping job posting: {e}")
        
        # 2. Scrape Glassdoor interview reviews
        try:
            glassdoor_data = await self._scrape_glassdoor_interviews(company)
            if glassdoor_data:
                all_raw_data.append({
                    "source_name": "Glassdoor Interviews",
                    "data": glassdoor_data
                })
        except Exception as e:
            print(f"Warning: Error scraping Glassdoor: {e}")
        
        # 3. Scrape company info from their careers page
        try:
            company_data = await self._scrape_company_info(company)
            if company_data:
                all_raw_data.append({
                    "source_name": "Company Info",
                    "data": company_data
                })
        except Exception as e:
            print(f"Warning: Error scraping company info: {e}")
        
        # Update state
        state["raw_scraped_data"] = all_raw_data
        state["session_ids"] = ["direct-scrape"]  # No session IDs needed
        
        return state
    
    async def _analyze_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """
        LangGraph Node 2: Analyze raw data with Groq/Llama using LangChain.
        """
        print(f"🤖 Analyzing with Groq ({settings.groq_model})...")
        
        # Combine raw text
        raw_text_parts: list[str] = []
        for item in state["raw_scraped_data"]:
            raw_text_parts.append(f"\n=== {item['source_name']} ===\n")
            raw_text_parts.append(json.dumps(item["data"], indent=2))
        
        combined_raw_text = "\n".join(raw_text_parts)[:20000]  # Increased to 20k chars
        
        # Create LangChain messages
        system_msg = SystemMessage(content="""You are a senior interview coach with 15+ years of experience helping candidates prepare for technical interviews at top companies. You excel at analyzing job postings, interview experiences, and company data to create comprehensive interview preparation materials.

Your analysis must be:
- DETAILED: Extract every specific detail, skill, requirement, and question mentioned
- ACTIONABLE: Provide concrete preparation tips, not generic advice
- STRUCTURED: Follow the exact JSON schema provided
- INFERENTIAL: Read between the lines - if a job posting mentions "distributed systems", infer they'll ask about scalability, consensus algorithms, etc.""")
        
        user_msg = HumanMessage(content=f"""Analyze ALL available data about {state['company_name']} for the {state['position']} position and create a comprehensive interview preparation guide.

Company: {state['company_name']}
Position: {state['position']}

RAW SCRAPED DATA:
{combined_raw_text}

CRITICAL INSTRUCTIONS:

1. **Job Posting Analysis** - If a job posting is included:
   - Extract EVERY skill, technology, and requirement mentioned
   - Infer what interview questions will test each skill (e.g., "microservices" → design questions, "React" → component lifecycle)
   - Note experience level indicators (junior/mid/senior)
   - Identify key responsibilities that will be tested in interviews

2. **Interview Questions** - Generate 15-25 SPECIFIC questions:
   - Pull actual questions from interview experiences if available
   - For each skill in job posting, create 2-3 relevant questions
   - Include difficulty level and detailed preparation tips
   - Categories: behavioral, technical, system_design, coding, role_specific, culture_fit
   - Example: Not "Tell me about yourself" but "Describe a time you debugged a production issue in a distributed system"

3. **Technical Requirements** - From job posting:
   - List ALL programming languages, frameworks, tools, cloud platforms mentioned
   - Identify must-have vs nice-to-have skills
   - Note any certifications or domain knowledge required

4. **Interview Process** - Structure with stages:
   - Phone screen, technical screen, onsite rounds, behavioral, system design, etc.
   - Realistic duration estimates (e.g., "45-60 minutes")
   - Format (video call, in-person, take-home, live coding)

5. **Preparation Tips** - Must be SPECIFIC:
   - Not "Practice coding" but "Focus on graph algorithms and dynamic programming - common for this role"
   - "Review [specific technology] documentation, especially [specific features]"
   - "Prepare 3 STAR stories about [specific scenarios from job posting]"

6. **Company Culture** - Extract from any company info:
   - Values, mission, work style
   - What they emphasize in job posting (innovation, collaboration, ownership, etc.)

Respond with ONLY valid JSON in this EXACT structure:
{{
  "company_overview": {{
    "name": "string",
    "industry": "string or null",
    "size": "string or null", 
    "headquarters": "string or null",
    "mission": "string or null",
    "culture": "string or null",
    "recent_news": ["array", "of", "strings"]
  }},
  "interview_questions": [
    {{
      "question": "Specific question text",
      "category": "technical|behavioral|system_design|coding|role_specific|culture_fit",
      "difficulty": "easy|medium|hard",
      "tips": "Detailed preparation tip for this question"
    }}
  ],
  "interview_process": {{
    "stages": [
      {{
        "name": "Stage name",
        "description": "What happens in this stage",
        "duration": "Time estimate",
        "format": "video_call|in_person|phone|take_home"
      }}
    ],
    "total_duration": "Full process duration",
    "preparation_tips": ["Specific tip 1", "Specific tip 2"]
  }},
  "technical_requirements": {{
    "programming_languages": ["Java", "Python"],
    "frameworks_tools": ["Spring Boot", "Docker"],
    "concepts": ["Microservices", "REST APIs"],
    "experience_level": "junior|mid|senior"
  }},
  "what_they_look_for": ["Leadership", "Problem solving"],
  "red_flags_to_avoid": ["Lack of teamwork", "No questions"],
  "salary_range": "string or null"
}}""")
        
        try:
            # Use LangChain to call Gemini
            response = await self.llm.ainvoke([system_msg, user_msg])
            
            # Parse JSON response
            content = response.content
            if isinstance(content, str):
                # Clean markdown code blocks if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                analysis = json.loads(content)
                state["llm_analysis"] = analysis
            else:
                state["error"] = "Invalid response format from LLM"
                
        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            state["error"] = str(e)
        
        return state
    
    def _structure_node(self, state: InterviewPrepState) -> InterviewPrepState:
        """
        LangGraph Node 3: Convert LLM output to Pydantic models.
        """
        print("📦 Structuring response...")
        
        if state.get("error") or not state.get("llm_analysis"):
            # Create fallback response
            state["final_response"] = self._create_fallback_response(
                state["company_name"],
                state["session_ids"]
            )
            return state
        
        try:
            analysis = state["llm_analysis"]
            if analysis is None:
                raise ValueError("LLM analysis is None")
            
            state["final_response"] = self._convert_llm_to_response(
                state["company_name"],
                analysis,
                state["session_ids"]
            )
        except Exception as e:
            print(f"Error structuring response: {e}")
            state["final_response"] = self._create_fallback_response(
                state["company_name"],
                state["session_ids"]
            )
        
        return state
    
    async def scrape_company_data(
        self, 
        request: CompanySearchRequest
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
            "job_url": str(request.job_posting_url) if request.job_posting_url else None,
            "raw_scraped_data": [],
            "session_ids": [],
            "llm_analysis": None,
            "final_response": None,
            "error": None
        }
        
        # Run the workflow
        final_state: InterviewPrepState = await self.workflow.ainvoke(initial_state)  # type: ignore[misc]
        
        # Return the final response
        if final_state["final_response"]:
            return final_state["final_response"]
        else:
            # Fallback
            return self._create_fallback_response(
                request.company_name,
                final_state.get("session_ids", [])  # type: ignore[arg-type]
            )
    
    def _convert_llm_to_response(
        self,
        company_name: str,
        llm_analysis: dict[str, Any],
        session_ids: list[str]
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
            recent_news=recent_news
        )
        
        # Parse interview questions
        questions: list[InterviewQuestion] = []
        for q in llm_analysis.get("interview_questions", [])[:20]:  # Limit to 20
            try:
                questions.append(InterviewQuestion(
                    question=q.get("question", ""),
                    category=q.get("category", "behavioral"),
                    difficulty=q.get("difficulty"),
                    tips=q.get("tips")
                ))
            except Exception:
                continue
        
        # Parse interview stages
        stages: list[InterviewStage] = []
        process_data = llm_analysis.get("interview_process", {})
        for stage in process_data.get("stages", []):
            try:
                stages.append(InterviewStage(
                    stage_name=stage.get("name", stage.get("stage_name", "Unknown")),
                    description=stage.get("description"),
                    duration=stage.get("duration"),
                    format=stage.get("format")
                ))
            except Exception:
                continue
        
        interview_process = InterviewProcess(
            stages=stages,
            total_duration=process_data.get("total_duration"),
            preparation_tips=process_data.get("preparation_tips", [])
        )
        
        # Parse technical requirements
        tech_data = llm_analysis.get("technical_requirements")
        technical_requirements = None
        if tech_data:
            technical_requirements = TechnicalRequirements(
                programming_languages=tech_data.get("programming_languages", []),
                frameworks_tools=tech_data.get("frameworks_tools", []),
                concepts=tech_data.get("concepts", []),
                experience_level=tech_data.get("experience_level")
            )
        
        # Build insights
        interview_insights = InterviewInsights(
            common_questions=questions,
            interview_process=interview_process,
            technical_requirements=technical_requirements,
            what_they_look_for=llm_analysis.get("what_they_look_for", []),
            red_flags_to_avoid=llm_analysis.get("red_flags_to_avoid", []),
            salary_range=llm_analysis.get("salary_range")
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
                "processing_pipeline": "custom_scrape -> groq_llama_analysis -> langgraph"
            }
        )
    
    def _create_fallback_response(
        self,
        company_name: str,
        session_ids: list[str]
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
                recent_news=[]
            ),
            interview_insights=InterviewInsights(
                common_questions=[],
                interview_process=InterviewProcess(
                    stages=[],
                    total_duration=None,
                    preparation_tips=[]
                ),
                technical_requirements=None,
                what_they_look_for=[],
                red_flags_to_avoid=[],
                salary_range=None
            ),
            sources=[],
            session_id=session_ids[0] if session_ids else "no-session",
            metadata={"error": "Failed to analyze data"}
        )
    
    async def scrape_company_data_stream(
        self,
        request: CompanySearchRequest
    ) -> AsyncGenerator[ScrapingProgressUpdate, None]:
        """
        Stream company data scraping progress via LangGraph workflow.
        
        Shows progress through: scrape → analyze → structure stages
        """
        yield ScrapingProgressUpdate(
            status="started",
            message=f"🔍 Starting LangGraph pipeline for {request.company_name}",
            progress_percent=0
        )
        
        # Initialize state
        initial_state: InterviewPrepState = {
            "company_name": request.company_name,
            "position": request.position or "general position",
            "job_url": str(request.job_posting_url) if request.job_posting_url else None,
            "raw_scraped_data": [],
            "session_ids": [],
            "llm_analysis": None,
            "final_response": None,
            "error": None
        }
        
        # Execute workflow with progress updates
        try:
            # Stage 1: Scraping
            yield ScrapingProgressUpdate(
                status="in_progress",
                message="📊 Node 1: Scraping job postings, Glassdoor & company info...",
                progress_percent=10
            )
            
            final_state: InterviewPrepState = await self.workflow.ainvoke(initial_state)  # type: ignore[misc]
            
            yield ScrapingProgressUpdate(
                status="complete",
                message=f"🎉 Pipeline complete for {request.company_name}!",
                progress_percent=100,
                session_id=final_state.get("session_ids", [None])[0],  # type: ignore[arg-type]
                data=final_state.get("final_response")  # type: ignore[arg-type]
            )
        
        except Exception as e:
            yield ScrapingProgressUpdate(
                status="error",
                message=f"❌ Error in pipeline: {str(e)}",
                progress_percent=0
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
                    "url": url
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
                    if len(text) > 100 and any(keyword in text.lower() for keyword in ["interview", "question", "process", "round"]):
                        interviews.append(text[:1000])
                    
                    if len(interviews) >= 10:  # Limit to 10 interviews
                        break
                
                if not interviews:
                    # Fallback: get all text
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    return {"content": text[:8000]}
                
                return {
                    "interviews": interviews,
                    "count": len(interviews)
                }
        except Exception as e:
            print(f"Error scraping Glassdoor: {e}")
            return None
    
    async def _scrape_company_info(self, company: str) -> dict[str, Any] | None:
        """Scrape company information from their careers/about page."""
        try:
            # Try to find company careers page
            search_query = f"{company} careers about culture"
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
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
                
                return {
                    "company": company,
                    "info": results
                }
        except Exception as e:
            print(f"Error scraping company info: {e}")
            return None
