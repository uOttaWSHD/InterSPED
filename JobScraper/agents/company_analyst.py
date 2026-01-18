from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import json
from models import CompanyOverview, TechnicalRequirements


class CompanyAnalystOutput(BaseModel):
    company_overview: CompanyOverview
    technical_requirements: TechnicalRequirements
    what_they_look_for: List[str] = Field(default_factory=list)
    salary_range: Optional[str] = None


async def run_company_analyst(
    state: Any, llm: Any, prompt_optimizer: Any
) -> Dict[str, Any]:
    print("\n🔍" + "🔍" * 10 + " [AGENT START: Company Analyst] " + "🔍" * 10)

    # Extract combined text from raw scraped data
    parts = []
    for item in state["raw_scraped_data"]:
        if item["source_name"] in ["Job Posting", "Company Info"]:
            parts.append(
                f"=== {item['source_name']} ===\n{json.dumps(item['data'], indent=2)}"
            )
    context = "\n".join(parts)[:15000]

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

        result = await structured_llm.ainvoke(messages)
        print(
            f"📄 [RAW OUTPUT: Company Analyst]\n{json.dumps(result.model_dump(), indent=2)}"
        )

        return {
            "company_overview": result.company_overview.model_dump(),
            "technical_requirements": result.technical_requirements.model_dump(),
            "what_they_look_for": result.what_they_look_for,
            "salary_range": result.salary_range,
        }
    except Exception as e:
        print(f"❌ [AGENT ERROR: Company Analyst] {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return {}
