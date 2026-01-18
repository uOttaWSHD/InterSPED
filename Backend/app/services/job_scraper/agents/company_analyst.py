from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import json
from ..models import CompanyOverview, TechnicalRequirements
from ..context_optimizer import optimize_context
from ..tpm_limiter import tpm_limiter


class CompanyAnalystOutput(BaseModel):
    company_overview: CompanyOverview
    technical_requirements: TechnicalRequirements
    what_they_look_for: List[str] = Field(default_factory=list)
    salary_range: Optional[str] = None


async def run_company_analyst(
    state: Any, llm: Any, prompt_optimizer: Any
) -> Dict[str, Any]:
    print("\n🔍" + "🔍" * 10 + " [AGENT START: Company Analyst] " + "🔍" * 10)

    # Use optimized context
    context = optimize_context(state["raw_scraped_data"], max_chars=6000)

    print(f"📊 [CONTEXT: Company Analyst] {len(context)} chars")

    prompt_template = prompt_optimizer.get_agent_prompt(
        "company_analyst", state["company_name"], state["position"], context
    )

    try:
        structured_llm = llm.with_structured_output(CompanyAnalystOutput)
        messages = prompt_template.format_messages(
            company_name=state["company_name"],
            position=state["position"],
            scraped_data=context,
        )

        # TPM Limiting
        estimated = tpm_limiter.estimate_tokens(str(messages))
        await tpm_limiter.wait_for_capacity(estimated)

        result = await structured_llm.ainvoke(messages)
        return {
            "company_overview": result.company_overview.model_dump(),
            "technical_requirements": result.technical_requirements.model_dump(),
            "what_they_look_for": result.what_they_look_for,
            "salary_range": result.salary_range,
        }
    except Exception as e:
        print(f"❌ [AGENT ERROR: Company Analyst] {type(e).__name__}: {e}")
        return {}
