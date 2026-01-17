"""
Static Prompt Templates for Interview Reconstruction.
Prompts are pre-optimized and used at runtime without dynamic re-optimization.
"""

from __future__ import annotations
import json
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage


class PromptOptimizer:
    """
    Provides pre-optimized static prompts for interview reconstruction.
    """

    def __init__(self) -> None:
        self.system_message = """You are an elite interview preparation specialist with 20+ years of experience at FAANG companies. Your mission is to create HYPER-DETAILED interview preparation materials that are so specific and comprehensive that a human or AI agent could use them to:

1. RECONSTRUCT realistic interview conversations word-for-word
2. PRACTICE answering with company-specific context and terminology  
3. ANTICIPATE exact follow-up questions and edge cases
4. UNDERSTAND what "good" vs "excellent" answers look like at THIS specific company

Your analysis must be:
- RECONSTRUCTABLE: Include enough detail that someone could role-play an actual interview
- COMPANY-SPECIFIC: Use the company's values, terminology, and cultural context in questions
- EXAMPLE-DRIVEN: Provide sample answers using STAR method, sample code, sample system designs
- FORENSIC: Extract EVERY skill mentioned and predict exactly how it will be tested
- REALISTIC: Include realistic interview flow, timing, interviewer behavior patterns

CRITICAL: OUTPUT MUST BE VALID JSON ONLY. NO PREAMBLE. NO MARKDOWN."""

        self.human_template = """Create an INTERVIEW RECONSTRUCTION GUIDE for {company_name} - {position} position.

Company: {company_name}
Position: {position}

RAW DATA SOURCES:
{scraped_data}

═══════════════════════════════════════════════════════════════════
YOUR MISSION - CRITICAL INSTRUCTIONS:
═══════════════════════════════════════════════════════════════════

1. INTERVIEW QUESTIONS (Generate 20-30 HYPER-SPECIFIC questions):
   Include EXACT wording, 2-3 paragraph sample answers, key points, follow-ups, and red flags.

2. CODING PROBLEMS:
   Include full statement, examples, constraints, approach hints, and optimal complexity.

3. SYSTEM DESIGN QUESTIONS (5-8 questions):
   Include scope, key components, evaluation criteria, and common approaches.

4. MOCK INTERVIEW SCENARIOS (2-3 scenarios):
   Include word-for-word opening/closing scripts and question sequences.

RESPOND WITH VALID JSON MATCHING THIS SCHEMA:
{{
  "company_overview": {{ "name": "...", "industry": "...", "culture": "...", "recent_news": [] }},
  "interview_questions": [ {{ "question": "...", "sample_answer": "...", "follow_up_questions": [], "red_flags": [] }} ],
  "coding_problems": [ {{ "title": "...", "problem_statement": "...", "leetcode_number": 0 }} ],
  "system_design_questions": [ {{ "question": "...", "scope": "..." }} ],
  "mock_scenarios": [ {{ "scenario_title": "...", "opening": "...", "questions_sequence": [] }} ],
  "interview_process": {{
    "stages": [
      {{
        "stage_name": "...",
        "description": "...",
        "duration": "...",
        "focus_areas": [],
        "sample_questions": [],
        "success_criteria": []
      }}
    ],
    "total_duration": "..."
  }},
  "technical_requirements": {{ "must_have_skills": [], "nice_to_have_skills": [] }},
  "what_they_look_for": [],
  "red_flags_to_avoid": [],
  "company_values_in_interviews": []
}}"""

    def get_static_prompt(
        self, company_name: str, position: str, scraped_data: str
    ) -> list[BaseMessage]:
        """Get formatted messages using static pre-optimized templates."""
        prompt_template = ChatPromptTemplate.from_messages(
            [("system", self.system_message), ("human", self.human_template)]
        )

        return prompt_template.format_messages(
            company_name=company_name, position=position, scraped_data=scraped_data
        )


def create_prompt_optimizer() -> PromptOptimizer:
    """Factory function to create prompt optimizer."""
    return PromptOptimizer()
