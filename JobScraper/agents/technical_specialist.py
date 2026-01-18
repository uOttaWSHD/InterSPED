from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import json
from models import CodingProblem, SystemDesignQuestion
from context_optimizer import optimize_context
from tpm_limiter import tpm_limiter


class TechnicalSpecialistOutput(BaseModel):
    coding_problems: List[CodingProblem] = Field(default_factory=list)
    system_design_questions: List[SystemDesignQuestion] = Field(default_factory=list)
    red_flags_to_avoid: List[str] = Field(default_factory=list)


async def run_technical_specialist(
    state: Any, llm: Any, prompt_optimizer: Any
) -> Dict[str, Any]:
    print("\n" + "🛠️" * 10 + " [AGENT START: Technical Specialist] " + "🛠️" * 10)

    # Use optimized context
    context = optimize_context(state["raw_scraped_data"], max_chars=8000)

    prompt_template = prompt_optimizer.get_agent_prompt(
        "technical_specialist", state["company_name"], state["position"], context
    )

    try:
        structured_llm = llm.with_structured_output(TechnicalSpecialistOutput)
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
            "coding_problems": [p.model_dump() for p in result.coding_problems],
            "system_design": [sd.model_dump() for sd in result.system_design_questions],
            "red_flags_to_avoid": result.red_flags_to_avoid,
        }
    except Exception as e:
        print(f"❌ [AGENT ERROR: Technical Specialist] {type(e).__name__}: {e}")
        return {}
