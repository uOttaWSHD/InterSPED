"""
Loader for Specialized Agent Prompt Templates.
Prompts are pre-optimized and loaded from static config files.
"""

from __future__ import annotations
import json
import os
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from config import settings


class PromptOptimizer:
    """
    Loads pre-optimized static prompts for specialized agents.
    """

    def __init__(self) -> None:
        self.agent_configs: dict[str, dict[str, Any]] = {}
        self._load_agent_configs()

    def _load_agent_configs(self) -> None:
        """Loads all agent configurations from the prompts/agents directory."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        agents_dir = os.path.join(current_dir, "prompts", "agents")

        agent_files = {
            "company_analyst": "company_analyst.json",
            "interview_architect": "interview_architect.json",
            "question_strategist": "question_strategist.json",
            "technical_specialist": "technical_specialist.json",
        }

        for agent_id, filename in agent_files.items():
            path = os.path.join(agents_dir, filename)
            try:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.agent_configs[agent_id] = json.load(f)
                else:
                    rel_path = os.path.join("JobScraper", "prompts", "agents", filename)
                    if os.path.exists(rel_path):
                        with open(rel_path, "r", encoding="utf-8") as f:
                            self.agent_configs[agent_id] = json.load(f)
                    else:
                        print(f"⚠️ Agent prompt file missing: {path}")
            except Exception as e:
                print(f"⚠️ Failed to load agent prompt {agent_id}: {e}")

    def get_agent_prompt(
        self, agent_id: str, company_name: str, position: str, scraped_data: str
    ) -> ChatPromptTemplate:
        """Get a ChatPromptTemplate for a specific agent."""
        config = self.agent_configs.get(
            agent_id,
            {
                "instructions": "You are a specialized agent.",
                "human_template": "Analyze data for {company_name} - {position}:\n{scraped_data}",
                "demos": [],
            },
        )

        system_msg = config.get("instructions", "")
        human_tpl = config.get("human_template", "")
        demos = config.get("demos", [])

        # Build demos text separately to avoid template formatting issues
        demos_text = ""
        if demos:
            demos_text += "\n\nFEW-SHOT EXAMPLES:\n"
            for demo in demos:
                input_ex = demo.get("input") or demo.get("company_context") or ""
                output_ex = demo.get("output") or demo.get("reconstruction_json") or ""
                # Escape curly braces for literal display in prompt to avoid format() errors
                safe_input = str(input_ex).replace("{", "{{").replace("}", "}}")
                safe_output = str(output_ex).replace("{", "{{").replace("}", "}}")
                demos_text += f"\nExample Input:\n{safe_input[:500]}\nExample Output:\n{safe_output}\n"

        # Create template with a placeholder for demos
        prompt = ChatPromptTemplate.from_messages(
            [("system", system_msg), ("human", human_tpl + "\n{demos_text}")]
        )

        # Partially fill the demos_text so it's treated as literal text, not a template
        return prompt.partial(demos_text=demos_text)


def create_prompt_optimizer() -> PromptOptimizer:
    """Factory function to create prompt optimizer."""
    return PromptOptimizer()
