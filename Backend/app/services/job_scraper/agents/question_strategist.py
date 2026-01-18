from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import json
from ..models import InterviewQuestion
from ..context_optimizer import optimize_context
from ..tpm_limiter import tpm_limiter


class QuestionStrategistOutput(BaseModel):
    common_questions: List[InterviewQuestion] = Field(default_factory=list)
    company_values_in_interviews: List[str] = Field(default_factory=list)


async def run_question_strategist(
    state: Any, llm: Any, prompt_optimizer: Any
) -> Dict[str, Any]:
    print("\n" + "🧠" * 10 + " [AGENT START: Question Strategist] " + "🧠" * 10)

    # Use optimized context
    context = optimize_context(state["raw_scraped_data"], max_chars=8000)

    prompt_template = prompt_optimizer.get_agent_prompt(
        "question_strategist", state["company_name"], state["position"], context
    )

    try:
        structured_llm = llm.with_structured_output(QuestionStrategistOutput)
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
            "common_questions": [q.model_dump() for q in result.common_questions],
            "company_values": result.company_values_in_interviews,
        }
    except Exception as e:
        print(f"❌ [AGENT ERROR: Question Strategist] {type(e).__name__}: {e}")
        return {}
