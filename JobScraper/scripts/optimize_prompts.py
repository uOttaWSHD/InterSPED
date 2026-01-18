"""
Programmatic Prompt Optimization using DSPy.
Optimizes both LeetCode extraction and Interview Reconstruction prompts.
Strictly uses moonshotai/kimi-k2-instruct-0905.
"""

import os
import json
import dspy
import asyncio
import random
from typing import Any, Optional
import sys
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.getcwd(), "JobScraper", ".env"))

# Add JobScraper to path
sys.path.append(os.path.join(os.getcwd(), "JobScraper"))

from leetcode_scraper import LeetCodeScraper
from config import settings

# --- 1. LeetCode Extraction Optimization ---


class LeetCodeExtractionSignature(dspy.Signature):
    """
    Extract structured LeetCode problem details from HTML content.
    Return a valid JSON object with: leetcode_number, title, difficulty, problem_statement,
    examples, constraints, example_input, example_output, optimal_time_complexity, optimal_space_complexity.
    """

    html_content = dspy.InputField()
    extracted_json = dspy.OutputField()


class LeetCodeExtractor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.extractor = dspy.ChainOfThought(LeetCodeExtractionSignature)

    def forward(self, html_content):
        return self.extractor(html_content=html_content)


def validate_leetcode_json(example, pred, trace=None):
    try:
        res = (
            json.loads(pred.extracted_json)
            if isinstance(pred.extracted_json, str)
            else pred.extracted_json
        )
        required = ["leetcode_number", "title", "problem_statement", "constraints"]
        return all(k in res for k in required)
    except:
        return False


# --- Main Optimization Logic ---


async def run_optimization():
    # Use the unified API key from settings (which handles the GROQ_API_KEY alias)
    from config import settings

    api_key = settings.llm_api_key

    if not api_key:
        print("❌ Error: llm_api_key (or GROQ_API_KEY) is not set. Cannot proceed.")
        return

    print("🤖 Starting optimization pipeline using Groq to bake prompts...")

    # Configure DSPy LM for Groq
    lm = dspy.LM(
        "groq/llama-3.3-70b-versatile",
        api_key=api_key,
        cache=True,
    )
    dspy.settings.configure(lm=lm)

    scraper = LeetCodeScraper()

    # 1. Optimize LeetCode Extraction
    samples_dir = "JobScraper/data/optimization/leetcode_samples"
    if os.path.exists(samples_dir):
        print("🚀 Optimizing LeetCode Extraction...")
        trainset = []
        html_files = [f for f in os.listdir(samples_dir) if f.endswith(".html")]
        random.shuffle(html_files)
        for f_name in html_files[:10]:
            with open(os.path.join(samples_dir, f_name), "r") as f:
                html = f.read()
            # Generate targets via forensic parser
            target = scraper._parse_leetcode_page(html, None, "http://mock")
            trainset.append(
                dspy.Example(
                    html_content=html[:3000], extracted_json=json.dumps(target)
                ).with_inputs("html_content")
            )

        teleprompter = dspy.BootstrapFewShot(
            metric=validate_leetcode_json, max_labeled_demos=2, max_bootstrapped_demos=2
        )
        compiled_leetcode = teleprompter.compile(LeetCodeExtractor(), trainset=trainset)

        # Save compiled state
        # In DSPy, demos are in the predictors.
        # ChainOfThought has a predictor at self.extractor
        # Wait, compiled_leetcode is LeetCodeExtractor, which has self.extractor (ChainOfThought)
        # ChainOfThought has self.predict
        demos = []
        if hasattr(compiled_leetcode.extractor, "demos"):
            demos = compiled_leetcode.extractor.demos
        elif hasattr(compiled_leetcode.extractor, "predict") and hasattr(
            compiled_leetcode.extractor.predict, "demos"
        ):
            demos = compiled_leetcode.extractor.predict.demos

        prompt_instructions = LeetCodeExtractionSignature.__doc__
        prompt_config = {
            "instructions": prompt_instructions.strip()
            if prompt_instructions
            else "Extract LeetCode problem details.",
            "demos": [
                {"input_snippet": d.html_content, "output": d.extracted_json}
                for d in demos
                if hasattr(d, "extracted_json")
            ],
            "format": "JSON",
        }
        os.makedirs(os.path.dirname(settings.leetcode_prompt_path), exist_ok=True)
        with open(settings.leetcode_prompt_path, "w") as f:
            json.dump(prompt_config, f, indent=2)
        print(f"✅ LeetCode prompt baked to {settings.leetcode_prompt_path}")

    # 2. Bake Interview Reconstruction Prompt
    print("🚀 Baking Interview Reconstruction prompt...")
    interview_config = {
        "system_message": "You are an elite interview preparation specialist. Your mission is to create HYPER-DETAILED interview preparation materials. OUTPUT MUST BE VALID JSON ONLY.",
        "human_template": """Create an INTERVIEW RECONSTRUCTION GUIDE for {company_name} - {position} position.
Company: {company_name}
Position: {position}
RAW DATA: {scraped_data}

SCHEMA:
{{
  "company_overview": {{ "name": "...", "industry": "...", "culture": "..." }},
  "interview_questions": [ {{ "question": "...", "sample_answer": "...", "red_flags": [] }} ],
  "coding_problems": [ {{ "title": "...", "problem_statement": "...", "leetcode_number": 0 }} ],
  "system_design_questions": [ {{ "question": "...", "scope": "..." }} ],
  "mock_scenarios": [ {{ "scenario_title": "...", "opening": "...", "questions_sequence": [] }} ],
  "interview_process": {{ "stages": [ {{"stage_name": "...", "description": "..."}}] }}
}}""",
        "demos": [],
    }
    os.makedirs(os.path.dirname(settings.interview_prompt_path), exist_ok=True)
    with open(settings.interview_prompt_path, "w") as f:
        json.dump(interview_config, f, indent=2)
    print(f"✅ Interview prompt baked to {settings.interview_prompt_path}")


if __name__ == "__main__":
    asyncio.run(run_optimization())
