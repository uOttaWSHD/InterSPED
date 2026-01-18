from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import json
from models import CodingProblem, SystemDesignQuestion


class TechnicalSpecialistOutput(BaseModel):
    coding_problems: List[CodingProblem] = Field(default_factory=list)
    system_design_questions: List[SystemDesignQuestion] = Field(default_factory=list)
    red_flags_to_avoid: List[str] = Field(default_factory=list)


async def run_technical_specialist(
    state: Any, llm: Any, prompt_optimizer: Any
) -> Dict[str, Any]:
    print("\n" + "🛠️" * 10 + " [AGENT START: Technical Specialist] " + "🛠️" * 10)

    parts = []
    for item in state["raw_scraped_data"]:
        if item["source_name"] in ["LeetCode Problems", "Job Posting"]:
            parts.append(
                f"=== {item['source_name']} ===\n{json.dumps(item['data'], indent=2)}"
            )
    context = "\n".join(parts)[:15000]

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
        result = await structured_llm.ainvoke(messages)
        print(
            f"📄 [RAW OUTPUT: Technical Specialist]\n{json.dumps(result.model_dump(), indent=2)}"
        )

        return {
            "coding_problems": [p.model_dump() for p in result.coding_problems],
            "system_design": [sd.model_dump() for sd in result.system_design_questions],
            "red_flags_to_avoid": result.red_flags_to_avoid,
        }
    except Exception as e:
        print(f"❌ [AGENT ERROR: Technical Specialist] {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return {}
