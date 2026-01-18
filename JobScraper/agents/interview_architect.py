from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import json
from models import InterviewProcess, MockInterviewScenario
from context_optimizer import optimize_context
from tpm_limiter import tpm_limiter


class InterviewArchitectOutput(BaseModel):
    interview_process: InterviewProcess
    mock_scenarios: List[MockInterviewScenario] = Field(default_factory=list)


async def run_interview_architect(
    state: Any, llm: Any, prompt_optimizer: Any
) -> Dict[str, Any]:
    print("\n" + "🏗️" * 10 + " [AGENT START: Interview Architect] " + "🏗️" * 10)

    # Use optimized context
    context = optimize_context(state["raw_scraped_data"], max_chars=6000)

    prompt_template = prompt_optimizer.get_agent_prompt(
        "interview_architect", state["company_name"], state["position"], context
    )

    try:
        structured_llm = llm.with_structured_output(InterviewArchitectOutput)
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
            "interview_process": result.interview_process.model_dump(),
            "mock_scenarios": [m.model_dump() for m in result.mock_scenarios],
        }
    except Exception as e:
        print(f"❌ [AGENT ERROR: Interview Architect] {type(e).__name__}: {e}")
        return {}
