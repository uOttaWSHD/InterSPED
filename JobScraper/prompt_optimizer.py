"""
LangChain/LangGraph Prompt Optimization Tools

This module provides prompt optimization utilities to help generate
extremely explicit interview reconstruction contracts.

Features:
- Few-shot example selectors
- Prompt templates with structured output
- Pydantic output parsers
- Dynamic example injection based on company/role similarity
"""

from __future__ import annotations
from typing import Any
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json


# ============================================================================
# FEW-SHOT EXAMPLES FOR INTERVIEW RECONSTRUCTION
# ============================================================================

INTERVIEW_RECONSTRUCTION_EXAMPLES = [
    {
        "company": "Amazon",
        "position": "Software Development Engineer II",
        "input": {
            "company_name": "Amazon",
            "position": "SDE II",
            "scraped_data": "Amazon values customer obsession, bias for action, ownership...",
        },
        "output": {
            "interview_questions": [
                {
                    "question": "Tell me about a time you had to make a decision with incomplete information. Walk me through your thought process, what data you gathered, and the outcome.",
                    "category": "behavioral",
                    "difficulty": "medium",
                    "sample_answer": "Situation: At my previous role, we had a production issue affecting 5% of users. Task: I needed to decide whether to rollback immediately or investigate first. Action: I gathered error logs, checked recent deployments, and consulted with the team. I decided to rollback within 10 minutes because customer impact was growing. Result: We prevented a larger outage, then investigated root cause post-rollback. I learned to always prioritize customer impact.",
                    "key_points_to_cover": [
                        "Decision-making under uncertainty",
                        "Data gathering",
                        "Customer impact consideration",
                        "Learning from outcomes",
                    ],
                    "follow_up_questions": [
                        "What if you had waited 5 more minutes?",
                        "How did you measure the impact?",
                        "What would you do differently?",
                    ],
                    "red_flags": [
                        "No clear decision process",
                        "Ignoring customer impact",
                        "No learning reflection",
                    ],
                    "company_specific_context": "Amazon's 'Bias for Action' principle - they want to see you can make decisions quickly with available data, not wait for perfect information.",
                }
            ],
            "coding_problems": [
                {
                    "title": "LRU Cache",
                    "difficulty": "medium",
                    "problem_statement": "Design and implement a data structure for a Least Recently Used (LRU) cache. It should support get and put operations.",
                    "company_specific_notes": "Amazon frequently asks this because it tests both data structure knowledge and system design thinking. They often follow up with: 'How would you make this distributed?'",
                }
            ],
            "mock_scenarios": [
                {
                    "scenario_title": "Technical Phone Screen - Amazon SDE II",
                    "opening": "Hi, I'm Sarah, a Senior Engineer at Amazon. This will be a 45-minute technical interview. We'll start with a brief intro, then move to a coding problem, and end with your questions. Let's begin: tell me about your experience with distributed systems.",
                    "questions_sequence": [
                        "Tell me about your experience with distributed systems",
                        "Design an LRU cache",
                        "How would you make this distributed across multiple servers?",
                        "What are the trade-offs of your approach?",
                    ],
                    "expected_flow": "Interviewer will probe deeply into system design trade-offs. They value clear thinking and customer impact considerations.",
                    "closing": "Great work today. We'll be in touch within 2-3 business days. Do you have any questions about Amazon or the role?",
                }
            ],
        },
    },
    {
        "company": "Google",
        "position": "Software Engineer L4",
        "input": {
            "company_name": "Google",
            "position": "SWE L4",
            "scraped_data": "Google values technical excellence, large-scale systems, algorithm expertise...",
        },
        "output": {
            "interview_questions": [
                {
                    "question": "Design a system to handle 1 billion requests per day for a search autocomplete feature. Walk me through your approach, including data structures, algorithms, and scalability considerations.",
                    "category": "system_design",
                    "difficulty": "hard",
                    "sample_answer": "I'd approach this in layers: 1) Client-side caching with Trie data structure for prefix matching, 2) Load balancers to distribute traffic, 3) In-memory cache (Redis) for hot queries, 4) Database sharding by query prefix, 5) Background job to update Trie from search logs. For 1B requests/day, we need ~11,500 req/s. I'd use consistent hashing for sharding and Bloom filters to reduce false positives.",
                    "key_points_to_cover": [
                        "Scalability",
                        "Data structure choice (Trie)",
                        "Caching strategy",
                        "Sharding approach",
                        "Trade-offs",
                    ],
                    "follow_up_questions": [
                        "How would you handle real-time updates?",
                        "What about multi-language support?",
                        "How do you ensure consistency?",
                    ],
                    "red_flags": [
                        "No scalability consideration",
                        "Single point of failure",
                        "No caching strategy",
                    ],
                    "company_specific_context": "Google emphasizes large-scale system design. They want to see you think about billions of users, not just thousands.",
                }
            ],
            "coding_problems": [
                {
                    "title": "Design Search Autocomplete System",
                    "difficulty": "hard",
                    "problem_statement": "Design a system that returns top K most frequent queries matching a given prefix. Handle 1B requests/day.",
                    "company_specific_notes": "Google often asks system design questions that combine algorithms with infrastructure. They expect you to discuss both the algorithm (Trie) and the system architecture.",
                }
            ],
        },
    },
    {
        "company": "Meta",
        "position": "Software Engineer E4",
        "input": {
            "company_name": "Meta",
            "position": "SWE E4",
            "scraped_data": "Meta values moving fast, building products, impact at scale...",
        },
        "output": {
            "interview_questions": [
                {
                    "question": "Tell me about a time you shipped a feature that had significant impact. What metrics did you track, and how did you iterate based on data?",
                    "category": "behavioral",
                    "difficulty": "medium",
                    "sample_answer": "Situation: I built a notification system that increased user engagement. Task: Ship feature and measure impact. Action: I tracked DAU, notification open rates, and conversion. After launch, I saw 15% increase in DAU but noticed some users were getting too many notifications. I added personalization to reduce notification fatigue. Result: DAU increased 25% while notification complaints dropped 40%.",
                    "key_points_to_cover": [
                        "Impact measurement",
                        "Data-driven iteration",
                        "User experience consideration",
                        "Scale thinking",
                    ],
                    "follow_up_questions": [
                        "How did you decide which metrics to track?",
                        "What was your iteration cycle?",
                        "How did you balance engagement vs. user experience?",
                    ],
                    "red_flags": [
                        "No metrics",
                        "No iteration",
                        "No consideration of negative impact",
                    ],
                    "company_specific_context": "Meta's 'Move Fast' culture - they want to see you can ship, measure, and iterate quickly based on data.",
                }
            ]
        },
    },
]


class PromptOptimizer:
    """
    LangChain-based prompt optimizer for interview reconstruction.

    Uses:
    - Few-shot examples to guide LLM output
    - Semantic similarity to select relevant examples
    - Structured output parsing with Pydantic
    - Prompt templates for consistency
    """

    def __init__(self) -> None:
        self.examples = INTERVIEW_RECONSTRUCTION_EXAMPLES
        self._build_prompt_templates()

    def _build_prompt_templates(self) -> None:
        """Build optimized prompt templates with few-shot examples."""

        # Example prompt template for few-shot learning
        example_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "human",
                    "Company: {company}\nPosition: {position}\n\nGenerate interview questions.",
                ),
                ("ai", "{output}"),
            ]
        )

        # Few-shot prompt template
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=self.examples,
        )

        # Final prompt template
        self.few_shot_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an elite interview preparation specialist. Your goal is to create HYPER-DETAILED interview materials that enable perfect interview reconstruction.

CRITICAL REQUIREMENTS:
1. Every question must include: exact wording, sample answer (2-3 paragraphs), key points, follow-ups, red flags, company context
2. Every coding problem must include: full statement, examples, constraints, approach hints, complexity, company-specific notes
3. Every mock scenario must include: exact opening script, question sequence, expected flow, closing script
4. Use company values and terminology throughout
5. Be specific enough that an AI agent could conduct a realistic interview

Here are examples of the level of detail required:""",
                ),
                few_shot_prompt,
                (
                    "human",
                    """Now generate interview materials for:
Company: {company_name}
Position: {position}

Scraped Data:
{scraped_data}

Generate comprehensive interview reconstruction materials following the examples above.""",
                ),
            ]
        )

    def get_optimized_prompt(
        self, company_name: str, position: str, scraped_data: str
    ) -> ChatPromptTemplate:
        """
        Get optimized prompt with few-shot examples.

        Args:
            company_name: Company name
            position: Job position
            scraped_data: Combined scraped data

        Returns:
            Optimized ChatPromptTemplate ready to format
        """
        # Select most relevant examples based on company/position similarity
        print(f"🧩 Optimizing prompt for {company_name} - {position}")
        try:
            relevant_examples = self._select_relevant_examples(company_name, position)
        except Exception as e:
            print(f"❌ Error selecting examples: {e}")
            # Fallback to first example
            relevant_examples = [self.examples[0]]

        # Build prompt with selected examples
        # Format examples for few-shot learning
        formatted_examples = []
        for ex in relevant_examples:
            formatted_examples.append(
                {
                    "company": ex["company"],
                    "position": ex["position"],
                    "output": json.dumps(ex["output"], indent=2),
                }
            )

        example_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "human",
                    "Company: {company}\nPosition: {position}\n\nGenerate interview questions.",
                ),
                ("ai", "{output}"),
            ]
        )

        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=formatted_examples,
        )

        # Build the full prompt template with placeholders
        final_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an elite interview preparation specialist with 20+ years of experience at FAANG companies. Your mission is to create HYPER-DETAILED interview preparation materials that are so specific and comprehensive that a human or AI agent could use them to:

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

Here are examples of the level of detail and specificity required:""",
                ),
                few_shot_prompt,
                (
                    "human",
                    """Create an INTERVIEW RECONSTRUCTION GUIDE for {company_name} - {position} position.

🎯 ULTIMATE GOAL: This guide must be SO DETAILED that:
- A human interviewer could use it to conduct an interview that candidates would believe is from {company_name}
- An AI agent could role-play as an interviewer and generate realistic, company-authentic conversations
- A candidate could practice and their answers would be evaluated as if by {company_name} interviewers
- Every question includes the EXACT wording, context, follow-ups, and evaluation criteria

Company: {company_name}
Position: {position}

RAW DATA SOURCES:
{scraped_data}

═══════════════════════════════════════════════════════════════════
YOUR MISSION - CRITICAL INSTRUCTIONS:
═══════════════════════════════════════════════════════════════════

IMPORTANT: OUTPUT MUST BE VALID JSON ONLY. NO PREAMBLE. NO MARKDOWN.
Just the raw JSON object starting with {{ and ending with }}.

1️⃣  INTERVIEW QUESTIONS (Generate 20-30 HYPER-SPECIFIC questions):

For EACH question include:
- The EXACT question wording (use company terminology)
- Sample EXCELLENT answer (2-3 paragraphs, STAR method for behavioral)
- Key points the interviewer is listening for
- 2-3 typical follow-up questions
- Red flags that would make the interviewer concerned
- Why THIS company asks THIS question (tie to their values)

Categories: behavioral, technical, coding, system_design, leadership, role_specific, culture_fit

Examples of SPECIFICITY we need:
❌ BAD: "Tell me about a time you solved a problem"
✅ GOOD: "Tell me about a time you debugged a P0 production incident affecting 10M+ users. Walk me through your incident response process, how you communicated with stakeholders, and what you learned."

❌ BAD: "How would you design Twitter?"
✅ GOOD: "Design a real-time notification system for 500M users with <100ms latency. Focus on: (1) Fan-out strategies, (2) Read vs write optimization, (3) Consistency trade-offs. I'll ask follow-ups about Redis vs Kafka."

CRITICAL: For EACH question, you MUST include:
1. The EXACT question as an interviewer would ask it (with company terminology)
2. A COMPLETE sample answer (2-3 paragraphs for behavioral, full solution for coding)
3. What the interviewer is LISTENING FOR (specific keywords, thought processes, red flags)
4. 2-3 REALISTIC follow-up questions the interviewer would ask
5. Company-specific context explaining WHY this company asks this (their values, culture, needs)
6. Red flags that would make the interviewer concerned or reject the candidate

═══════════════════════════════════════════════════════════════════

2️⃣  CODING PROBLEMS (If LeetCode data available):

For EACH problem include:
- Full problem statement
- Example inputs/outputs
- Constraints
- Topics/patterns it tests
- Approach hints
- Optimal complexity
- Company-specific context (e.g., "They ALWAYS ask follow-up about space optimization")

═══════════════════════════════════════════════════════════════════

3️⃣  SYSTEM DESIGN QUESTIONS (5-8 realistic questions):

For EACH include:
- The prompt (e.g., "Design YouTube's video recommendation engine")
- Expected scope and scale
- Key components they expect you to discuss
- Evaluation criteria (what they're really testing)
- Time allocation guide
- Common approaches
- Follow-up deep-dives

═══════════════════════════════════════════════════════════════════

4️⃣  MOCK INTERVIEW SCENARIOS (2-3 complete scenarios):

Create COMPLETE interview scripts:
- Opening (exact interviewer greeting)
- Question sequence (in order, with timing)
- Expected flow narrative
- Closing and Q&A time
- Good questions for candidate to ask

Example:
"Welcome to our technical interview. I'm Sarah, Senior Engineer. Today we'll do 10min intro, 35min coding, 10min your questions, 5min wrap-up. Let's start: tell me about your experience with distributed systems..."

═══════════════════════════════════════════════════════════════════

5️⃣  INTERVIEW PROCESS STAGES:

For EACH stage include:
- Stage name and format
- Duration
- Who interviews (role/seniority)
- Focus areas
- Sample questions from this specific stage
- Success criteria
- Preparation strategy

═══════════════════════════════════════════════════════════════════

6️⃣  TECHNICAL REQUIREMENTS:

Categorize as:
- MUST-HAVE (deal-breakers)
- NICE-TO-HAVE (bonus points)
- DOMAIN KNOWLEDGE (industry-specific)

For each skill, note how it's tested in interviews.

═══════════════════════════════════════════════════════════════════

7️⃣  COMPANY VALUES IN INTERVIEWS:

Identify company values and show EXACTLY how they manifest in interviews.

Example for Amazon:
- "Customer Obsession" → Expect questions like "Tell me about a time you advocated for a customer against internal priorities"
- "Bias for Action" → They value scrappy POCs over perfect designs
- "Frugality" → Design questions will probe cost optimization

═══════════════════════════════════════════════════════════════════

RESPOND WITH VALID JSON MATCHING THIS SCHEMA:

{{
  "company_overview": {{
    "name": "string",
    "industry": "string|null",
    "size": "string|null",
    "headquarters": "string|null", 
    "mission": "string|null",
    "culture": "string|null",
    "recent_news": ["string"]
  }},
  "interview_questions": [
    {{
      "question": "Hyper-specific question with context",
      "category": "behavioral|technical|coding|system_design|leadership|role_specific|culture_fit",
      "difficulty": "easy|medium|hard",
      "tips": "Detailed prep tips",
      "sample_answer": "Full example answer (2-3 paragraphs)",
      "key_points_to_cover": ["point1", "point2"],
      "follow_up_questions": ["follow-up 1", "follow-up 2"],
      "red_flags": ["red flag 1", "red flag 2"],
      "company_specific_context": "Why this company asks this"
    }}
  ],
  "coding_problems": [
    {{
      "title": "Problem name",
      "difficulty": "easy|medium|hard",
      "problem_statement": "Full description",
      "example_input": "string|null",
      "example_output": "string|null",
      "constraints": ["constraint"],
      "leetcode_number": 123,
      "leetcode_url": "string|null",
      "topics": ["topic"],
      "approach_hints": ["hint"],
      "optimal_time_complexity": "O(n)",
      "optimal_space_complexity": "O(1)",
      "frequency": "very_common|common|occasional|rare",
      "company_specific_notes": "They always ask..."
    }}
  ],
  "system_design_questions": [
    {{
      "question": "Design X",
      "scope": "100M users, global",
      "key_components": ["component"],
      "evaluation_criteria": ["criteria"],
      "common_approaches": ["approach"],
      "follow_up_topics": ["topic"],
      "time_allocation": "10min requirements, 30min design, 5min followup"
    }}
  ],
  "mock_scenarios": [
    {{
      "scenario_title": "Technical Phone Screen",
      "stage": "Phone Screen",
      "duration": "45-60 minutes",
      "opening": "Exact interviewer greeting...",
      "questions_sequence": ["Q1", "Q2", "Q3"],
      "expected_flow": "Narrative of how interview unfolds",
      "closing": "How it ends...",
      "time_for_candidate_questions": true,
      "good_questions_to_ask": ["question"]
    }}
  ],
  "interview_process": {{
    "stages": [
      {{
        "stage_name": "Stage name",
        "description": "What happens",
        "duration": "Time",
        "format": "video_call|in_person|phone|take_home",
        "interviewers": "Who conducts it",
        "focus_areas": ["area"],
        "sample_questions": ["question"],
        "success_criteria": ["criteria"],
        "preparation_strategy": "How to prep"
      }}
    ],
    "total_duration": "2-4 weeks",
    "preparation_tips": ["tip"]
  }},
  "technical_requirements": {{
    "programming_languages": ["lang"],
    "frameworks_tools": ["tool"],
    "concepts": ["concept"],
    "experience_level": "junior|mid|senior",
    "must_have_skills": ["skill"],
    "nice_to_have_skills": ["skill"],
    "domain_knowledge": ["domain"]
  }},
  "what_they_look_for": ["quality"],
  "red_flags_to_avoid": ["flag"],
  "salary_range": "string|null",
  "company_values_in_interviews": ["How value X shows up"]
}}

═══════════════════════════════════════════════════════════════════
FINAL CHECKLIST - Before responding, verify:
═══════════════════════════════════════════════════════════════════

✅ Every question has a COMPLETE sample answer (not just bullet points)
✅ Every coding problem includes full problem statement, examples, constraints, and approach
✅ Every mock scenario includes EXACT opening/closing scripts (word-for-word)
✅ Company values are woven into questions and evaluation criteria
✅ Follow-up questions are realistic and company-specific
✅ Technical requirements are categorized (must-have vs nice-to-have)
✅ Interview stages include who conducts them, duration, and success criteria
✅ The output is detailed enough that someone could role-play an entire interview

REMEMBER: This must be detailed enough to RECONSTRUCT an authentic interview that passes as real!""",
                ),
            ]
        )

        return final_prompt

    def _select_relevant_examples(
        self, company_name: str, position: str
    ) -> list[dict[str, Any]]:
        """
        Select most relevant few-shot examples based on company/position.

        For now, uses simple keyword matching. Could be enhanced with
        semantic similarity using embeddings.
        """
        company_lower = company_name.lower()
        position_lower = position.lower()

        # Simple relevance scoring
        scored_examples = []
        for example in self.examples:
            score = 0
            example_company = example["company"].lower()
            example_position = example["position"].lower()

            # Company match
            if company_lower in example_company or example_company in company_lower:
                score += 10
            elif any(word in example_company for word in company_lower.split()):
                score += 5

            # Position match
            if "engineer" in position_lower and "engineer" in example_position:
                score += 5
            if "senior" in position_lower and "senior" in example_position:
                score += 3

            scored_examples.append((score, example))

        # Sort by score and return top 2
        scored_examples.sort(key=lambda x: x[0], reverse=True)
        return [ex[1] for ex in scored_examples[:2]]

    def get_structured_output_parser(self) -> PydanticOutputParser | None:
        """
        Get Pydantic output parser for structured LLM responses.

        Note: This would require importing the actual Pydantic models.
        For now, we'll use JSON parsing in the service layer.
        """
        # This is a placeholder - actual implementation would use
        # PydanticOutputParser with the InterviewInsights model
        return None


def create_prompt_optimizer() -> PromptOptimizer:
    """Factory function to create prompt optimizer."""
    return PromptOptimizer()
