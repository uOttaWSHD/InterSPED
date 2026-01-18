from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import json
from models import InterviewProcess, MockInterviewScenario


class InterviewArchitectOutput(BaseModel):
    interview_process: InterviewProcess
    mock_scenarios: List[MockInterviewScenario] = Field(default_factory=list)


async def run_interview_architect(
    state: Any, llm: Any, prompt_optimizer: Any
) -> Dict[str, Any]:
    print("\n" + "🏗️" * 10 + " [AGENT START: Interview Architect] " + "🏗️" * 10)

    parts = []
    for item in state["raw_scraped_data"]:
        if item["source_name"] in ["Glassdoor Interviews", "Job Posting"]:
            parts.append(
                f"=== {item['source_name']} ===\n{json.dumps(item['data'], indent=2)}"
            )
    context = "\n".join(parts)[:15000]

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
        result = await structured_llm.ainvoke(messages)
        print(
            f"📄 [RAW OUTPUT: Interview Architect]\n{json.dumps(result.model_dump(), indent=2)}"
        )

        return {
            "interview_process": result.interview_process.model_dump(),
            "mock_scenarios": [m.model_dump() for m in result.mock_scenarios],
        }
    except Exception as e:
        print(f"❌ [AGENT ERROR: Interview Architect] {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return {}
