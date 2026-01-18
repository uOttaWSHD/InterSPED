"""
Direct test for ScraperService agents.
"""

import asyncio
import os
import json
import sys

# Add JobScraper to path
sys.path.append(os.path.join(os.getcwd(), "JobScraper"))

from service import ScraperService
from models import CompanySearchRequest


async def test_agents():
    print("🧪 [TEST] Starting Agent Output Verification...")
    service = ScraperService()

    # Mock request
    request = CompanySearchRequest(
        company_name="Royal Bank of Canada",
        position="Software Developer",
        job_posting_url="https://jobs.rbc.com/ca/en/job/R-0000152270/2026-Summer-Student-Opportunities-Capital-Markets-QTS-Software-Developer-4-months",
    )

    print(f"🔍 Running full pipeline for {request.company_name}...")
    result = await service.scrape_company_data(request)

    print("\n" + "=" * 50)
    print("📑 FINAL AGENT OUTPUT VERIFICATION")
    print("=" * 50)

    print(f"\n🏢 [COMPANY OVERVIEW]")
    print(json.dumps(result.company_overview.model_dump(), indent=2))

    print(f"\n💻 [TECHNICAL REQUIREMENTS]")
    print(
        json.dumps(
            result.interview_insights.technical_requirements.model_dump(), indent=2
        )
    )

    print(f"\n🏗️ [INTERVIEW PROCESS]")
    print(
        f"Total Duration: {result.interview_insights.interview_process.total_duration}"
    )
    print(f"Stages: {len(result.interview_insights.interview_process.stages)}")
    for stage in result.interview_insights.interview_process.stages:
        print(f"  - {stage.stage_name}: {stage.format}")

    print(f"\n🛠️ [TECHNICAL]")
    print(f"Coding Problems: {len(result.interview_insights.coding_problems)}")
    print(f"System Design: {len(result.interview_insights.system_design_questions)}")
    for sd in result.interview_insights.system_design_questions:
        print(f"  - {sd.question}")

    print(f"\n🧠 [QUESTIONS]")
    print(f"Common Questions: {len(result.interview_insights.common_questions)}")
    for q in result.interview_insights.common_questions[:3]:
        print(f"  - {q.question} ({q.category})")

    print("\n✅ Test Complete.")


if __name__ == "__main__":
    if not os.environ.get("LLM_API_KEY") and not os.environ.get("GROQ_API_KEY"):
        print("❌ Error: Set LLM_API_KEY or GROQ_API_KEY in environment.")
    else:
        asyncio.run(test_agents())
