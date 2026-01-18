"""
Targeted test for the Company Analyst agent.
"""

import asyncio
import os
import json
import sys
from pydantic import BaseModel, Field
from typing import List, Optional

# Add JobScraper to path
sys.path.append(os.path.join(os.getcwd(), "JobScraper"))

from service import ScraperService
from agents.company_analyst import CompanyAnalystOutput
from models import CompanySearchRequest


async def test_analyst():
    print("🧪 [TEST] Starting Company Analyst Targeted Verification...")
    service = ScraperService()
    # Override model for testing to avoid rate limits
    if "llama" in service.llm.model_name.lower():
        print("🔄 Overriding model to llama-3.1-8b-instant for testing...")
        from langchain_groq import ChatGroq

        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("GROQ_API_KEY")
        service.llm = ChatGroq(
            model="llama-3.1-8b-instant", temperature=0.1, groq_api_key=api_key
        )

    # Load example posting
    try:
        with open("JobScraper/example_posting.txt", "r") as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Failed to read example_posting.txt: {e}")
        return

    # Mock state
    state = {
        "company_name": "Royal Bank of Canada",
        "position": "Software Developer",
        "raw_scraped_data": [
            {"source_name": "Job Posting", "data": {"full_content": content}}
        ],
    }

    from agents.company_analyst import run_company_analyst

    result = await run_company_analyst(state, service.llm, service.prompt_optimizer)

    print("\n" + "=" * 50)
    print("📑 ANALYST OUTPUT VERIFICATION")
    print("=" * 50)
    print(json.dumps(result, indent=2))

    if result.get("technical_requirements", {}).get("programming_languages"):
        print("\n✅ SUCCESS: Programming languages extracted!")
    else:
        print("\n❌ FAILURE: Programming languages missing.")

    print("\n✅ Test Complete.")


if __name__ == "__main__":
    if not os.environ.get("LLM_API_KEY") and not os.environ.get("GROQ_API_KEY"):
        print("❌ Error: Set LLM_API_KEY or GROQ_API_KEY in environment.")
    else:
        asyncio.run(test_analyst())
