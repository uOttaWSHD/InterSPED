"""
LeetCode Company Problems Scraper

Scrapes company-specific LeetCode problems from:
1. Local data folder (cloned from liquidslr/leetcode-company-wise-problems)
2. LeetCode.ca for actual problem content

Architecture: Modular and swappable for Yellowcake integration.
Uses file-based caching to avoid duplicate scraping.
"""

from __future__ import annotations

import csv
import json
import os
import re
from typing import Optional, Any, TypedDict, cast

import httpx
from bs4 import BeautifulSoup, Tag

from cache import get_cache
from config import settings
from tpm_limiter import tpm_limiter


class LeetCodeProblemData(TypedDict, total=False):
    leetcode_number: Optional[int]
    title: Optional[str]
    difficulty: Optional[str]
    problem_statement: Optional[str]
    examples: list[str]
    constraints: list[str]
    url: str
    example_input: Optional[str]
    example_output: Optional[str]
    optimal_time_complexity: Optional[str]
    optimal_space_complexity: Optional[str]


class LeetCodeScraper:
    """
    Scrape company-specific LeetCode problems.
    Uses Yellowcake for extracting structured data from problem pages.
    """

    def __init__(self) -> None:
        self.cache = get_cache()
        # Local data path (cloned repo)
        self.data_dir = "/var/home/waaberi/Documents/uOttahack/Submission/JobScraper/data/leetcode_problems"
        self.leetcode_ca_base = "https://leetcode.ca"
        self.yellowcake_api_key = settings.yellowcake_api_key
        self.yellowcake_api_url = settings.yellowcake_api_url
        self.force_fallback = settings.force_yellowcake_fallback

        # Load optimized prompt from file
        self.yellowcake_prompt = self._load_optimized_prompt()

    def _load_optimized_prompt(self) -> str:
        """Loads the optimized prompt from the local JSON file."""
        import json
        import os

        # Use absolute path resolution
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(current_dir, "prompts", "leetcode_extraction.json")

        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                # Fallback to path in settings
                path = settings.leetcode_prompt_path
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                else:
                    raise FileNotFoundError(f"Prompt file not found at {path}")

            instructions = config.get("instructions", "")
            demos = config.get("demos", [])

            prompt = instructions + "\n\nEXAMPLES:\n"
            for demo in demos:
                snippet = demo.get("input_snippet") or demo.get("html_content") or ""
                output = demo.get("output") or demo.get("extracted_json") or ""
                prompt += f"\nInput: {snippet[:300]}...\nOutput: {output}\n"

            return prompt
        except Exception as e:
            print(f"⚠️ Failed to load optimized prompt: {e}")

        # Absolute fallback if file is missing
        return "Extract LeetCode problem details into JSON: leetcode_number, title, difficulty, problem_statement, examples, constraints, example_input, example_output, optimal_time_complexity, optimal_space_complexity."

    async def _scrape_with_yellowcake(
        self, url: str, prompt: str, priority: str = "high"
    ) -> Any | None:
        """
        Scrape a URL using Yellowcake API.
        """
        if self.force_fallback:
            print("🚫 [YELLOWCAKE] Force fallback enabled. Bypassing API.")
            return None

        if (
            not self.yellowcake_api_key
            or self.yellowcake_api_key == "your_api_key_here"
            or self.yellowcake_api_key == "mock"
        ):
            print("⚠️ [YELLOWCAKE] Invalid or missing API key.")
            return None

        print(f"🍰 [YELLOWCAKE] Scraping {url} (Priority: {priority})...")

        # Estimate tokens and wait for capacity
        estimated_tokens = tpm_limiter.estimate_tokens(prompt + url)
        await tpm_limiter.wait_for_capacity(estimated_tokens, priority=priority)

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.yellowcake_api_key,
        }

        payload = {
            "url": url,
            "prompt": prompt,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", self.yellowcake_api_url, headers=headers, json=payload
                ) as response:
                    if response.status_code != 200:
                        print(f"❌ [YELLOWCAKE] API error: {response.status_code}")
                        return None

                    final_data = None
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line.replace("data: ", "", 1)
                            try:
                                event_data = json.loads(data_str)
                                if (
                                    isinstance(event_data, dict)
                                    and event_data.get("success") is True
                                    and "data" in event_data
                                ):
                                    final_data = event_data.get("data")
                                    print("✅ [YELLOWCAKE] Received valid data chunk")
                            except json.JSONDecodeError:
                                pass

                    return final_data

        except Exception as e:
            print(f"❌ [YELLOWCAKE] Error: {e}")
            return None

    async def get_company_problems(
        self, company_name: str, limit: int = 20
    ) -> list[dict[str, str | int]]:
        """
        Get LeetCode problems asked by a specific company from local CSV files.
        """
        # Check cache first
        cached = self.cache.get_scraped_data(
            company=company_name, source="leetcode_problems"
        )

        if cached:
            print(f"✅ Cache hit for {company_name} LeetCode problems")
            return cast(list[dict[str, str | int]], cached[:limit])

        print(f"🔍 Searching local data for {company_name} LeetCode problems...")

        try:
            csv_data = await self._fetch_company_csv(company_name)

            if not csv_data:
                return []

            # Parse CSV and extract problem metadata
            problems = self._parse_csv_data(csv_data)

            # Cache the results
            self.cache.set_scraped_data(
                company=company_name, source="leetcode_problems", data=problems
            )

            return problems[:limit]

        except Exception as e:
            print(f"❌ Error fetching local LeetCode problems: {e}")
            return []

    async def get_problem_details(
        self,
        leetcode_number: int | None = None,
        problem_title: str | None = None,
        priority: str = "high",
    ) -> dict[str, Any] | None:
        """
        Get full problem details from leetcode.ca.
        """
        cache_key = (
            str(leetcode_number) if leetcode_number else (problem_title or "unknown")
        )

        # Check cache
        cached = self.cache.get_scraped_data(
            company="leetcode", source="problem_details", url=cache_key
        )

        if cached:
            return cast(dict[str, Any], cached)

        print(f"🔍 Scraping leetcode.ca for {cache_key} (Priority: {priority})...")

        try:
            # Scrape from leetcode.ca
            problem_data = await self._scrape_leetcode_ca(
                problem_number=leetcode_number,
                problem_title=problem_title,
                priority=priority,
            )

            if problem_data:
                # Cache it
                self.cache.set_scraped_data(
                    company="leetcode",
                    source="problem_details",
                    data=problem_data,
                    url=cache_key,
                )

            return problem_data

        except Exception as e:
            print(f"❌ Error scraping problem: {e}")
            return None

    async def enrich_with_details(
        self,
        problems: list[dict[str, str | int]],
        max_details: int = 10,
        sequential: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Enrich problem metadata with full details.
        """
        import asyncio

        subset = problems[:max_details]
        enriched: list[dict[str, Any]] = []

        if sequential:
            print(
                f"🐢 [QUEUE] Sequentially fetching details for {len(subset)} problems..."
            )
            for problem in subset:
                number = problem.get("leetcode_number")
                title = problem.get("title")
                details = None
                if number is not None and isinstance(number, int):
                    details = await self.get_problem_details(
                        leetcode_number=number, priority="low"
                    )
                elif title is not None and isinstance(title, str):
                    details = await self.get_problem_details(
                        problem_title=title, priority="low"
                    )

                if details:
                    enriched.append({**problem, **details})
                else:
                    enriched.append(problem)
                # Avoid hitting TPM too hard even with limiter
                await asyncio.sleep(0.5)
            return enriched

        tasks = []
        for i, problem in enumerate(subset):
            number = problem.get("leetcode_number")
            title = problem.get("title")

            if number is not None and isinstance(number, int):
                tasks.append(self.get_problem_details(leetcode_number=number))
            elif title is not None and isinstance(title, str):
                tasks.append(self.get_problem_details(problem_title=title))

        if not tasks:
            return subset

        print(f"⚡ [PARALLEL] Fetching details for {len(tasks)} problems...")
        results = await asyncio.gather(*tasks)

        for i, details in enumerate(results):
            original_problem = subset[i]
            if details:
                enriched_problem = {**original_problem, **details}
                if "leetcode_number" not in enriched_problem and "number" in details:
                    enriched_problem["leetcode_number"] = details["number"]
                enriched.append(enriched_problem)
            else:
                enriched.append(original_problem)

        return enriched

    async def _fetch_company_csv(self, company_name: str) -> Optional[str]:
        """
        Fetch CSV from local directory using aggressive matching and LLM resolution.
        """
        import difflib

        try:
            if not os.path.exists(self.data_dir):
                print(f"❌ Data directory missing: {self.data_dir}")
                return None

            company_dirs = [
                d
                for d in os.listdir(self.data_dir)
                if os.path.isdir(os.path.join(self.data_dir, d))
            ]

            search_names = [
                company_name.lower(),
                company_name.lower().replace(" ", ""),
                re.sub(r"[^a-z0-9]", "", company_name.lower()),
            ]

            if " " in company_name:
                abbrev = "".join(
                    word[0] for word in company_name.split() if word
                ).lower()
                if len(abbrev) >= 2:
                    search_names.append(abbrev)

            matched_dir = None
            for d in company_dirs:
                d_lower = d.lower().replace(" ", "")
                for target in search_names:
                    if target == d_lower or target in d_lower or d_lower in target:
                        matched_dir = d
                        break
                if matched_dir:
                    break

            if not matched_dir and settings.llm_api_key:
                print(f"🤖 Asking LLM to resolve company name: {company_name}")
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        prompt = f"Given a company name '{company_name}', return 3 potential directory names (short, common abbreviations, or legal names) that might represent it in a list of LeetCode company folders. Respond with only the names separated by commas. Example: 'Royal Bank of Canada' -> 'RBC, RoyalBank, RoyalBankofCanada'"
                        payload = {
                            "model": settings.llm_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                        }

                        api_url = "https://api.groq.com/openai/v1/chat/completions"
                        if "moonshot" in settings.llm_model.lower():
                            api_url = (
                                settings.llm_api_base
                                or "https://api.moonshot.cn/v1/chat/completions"
                            )
                        elif settings.llm_api_base:
                            api_url = (
                                f"{settings.llm_api_base.rstrip('/')}/chat/completions"
                            )

                        headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
                        response = await client.post(
                            api_url, headers=headers, json=payload
                        )
                        if response.status_code == 200:
                            content = response.json()["choices"][0]["message"][
                                "content"
                            ]
                            variations = [v.strip().lower() for v in content.split(",")]
                            for d in company_dirs:
                                d_clean = d.lower().replace(" ", "")
                                if any(
                                    v in d_clean or d_clean in v for v in variations
                                ):
                                    matched_dir = d
                                    break
                except Exception as e:
                    print(f"⚠️ LLM resolution failed: {e}")

            if not matched_dir:
                matches = difflib.get_close_matches(
                    company_name, company_dirs, n=1, cutoff=0.5
                )
                if matches:
                    matched_dir = matches[0]

            if matched_dir:
                dir_path = os.path.join(self.data_dir, matched_dir)
                files = os.listdir(dir_path)
                csv_file = next((f for f in files if f.lower() == "all.csv"), None)
                if not csv_file:
                    csv_file = next(
                        (f for f in files if "all" in f.lower() and f.endswith(".csv")),
                        None,
                    )
                if not csv_file:
                    csv_file = next((f for f in files if f.endswith(".csv")), None)

                if csv_file:
                    print(f"✅ Found local CSV: {matched_dir}/{csv_file}")
                    with open(
                        os.path.join(dir_path, csv_file), "r", encoding="utf-8"
                    ) as f:
                        return f.read()

            return None
        except Exception as e:
            print(f"❌ Discovery error: {e}")
            return None

    def _parse_csv_data(self, csv_text: str) -> list[dict[str, str | int]]:
        """Parse CSV metadata."""
        problems: list[dict[str, str | int]] = []
        reader = csv.DictReader(csv_text.strip().split("\n"))
        for row in reader:
            try:
                problem: dict[str, str | int] = {}
                if "ID" in row and row["ID"].strip():
                    problem["leetcode_number"] = int(row["ID"].strip())
                if "Title" in row:
                    problem["title"] = row["Title"]
                if "Difficulty" in row:
                    problem["difficulty"] = row["Difficulty"].lower()
                if "Link" in row:
                    problem["link"] = row["Link"]
                if "title" in problem:
                    if "difficulty" not in problem:
                        problem["difficulty"] = "medium"
                    problems.append(problem)
            except Exception:
                continue
        return problems

    async def discover_problem_link(
        self, problem_number: int | None = None, problem_title: str | None = None
    ) -> str | None:
        """Discovers the specific problem URL on leetcode.ca."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                resp = await client.get(self.leetcode_ca_base)
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "lxml")
                for link in soup.find_all("a"):
                    if not isinstance(link, Tag):
                        continue
                    inner_text = link.get_text(strip=True)
                    target_found = False
                    if problem_number:
                        num_str = str(problem_number)
                        if (
                            num_str == inner_text.split(".")[0].strip()
                            or num_str in inner_text.split()
                        ):
                            target_found = True
                    elif problem_title and problem_title.lower() in inner_text.lower():
                        target_found = True
                    if target_found:
                        href = link.get("href")
                        if href and isinstance(href, str):
                            if not href.startswith("http"):
                                href = f"{self.leetcode_ca_base.rstrip('/')}/{href.lstrip('/')}"
                            return href
                return None
            except Exception:
                return None

    async def _scrape_leetcode_ca(
        self,
        problem_number: int | None = None,
        problem_title: str | None = None,
        priority: str = "high",
    ) -> dict[str, Any] | None:
        """Discovers link and extracts data."""
        problem_link = await self.discover_problem_link(problem_number, problem_title)
        if not problem_link:
            return None

        if self.yellowcake_api_key:
            data = await self._scrape_with_yellowcake(
                problem_link, self.yellowcake_prompt, priority=priority
            )
            if data and isinstance(data, dict):
                return {
                    "leetcode_number": data.get("leetcode_number") or problem_number,
                    "title": data.get("title") or problem_title,
                    "difficulty": data.get("difficulty") or "medium",
                    "problem_statement": data.get("problem_statement"),
                    "examples": data.get("examples") or [],
                    "constraints": data.get("constraints") or [],
                    "example_input": data.get("example_input"),
                    "example_output": data.get("example_output"),
                    "optimal_time_complexity": data.get("optimal_time_complexity"),
                    "optimal_space_complexity": data.get("optimal_space_complexity"),
                    "url": problem_link,
                }

        print(f"🐚 Fallback: Manual BS4 scrape of {problem_link}")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(problem_link)
            if resp.status_code == 200:
                return self._parse_leetcode_page(
                    resp.text, problem_number, problem_link
                )
        return None

    def _parse_leetcode_page(
        self, html: str, number: int | None, url: str
    ) -> dict[str, Any]:
        """Forensic manual parsing based on leetcode.ca HTML structure."""
        soup = BeautifulSoup(html, "lxml")
        data: dict[str, Any] = {
            "url": url,
            "leetcode_number": number,
            "examples": [],
            "constraints": [],
            "problem_statement": "",
            "difficulty": "medium",
        }

        h1 = soup.find("h1")
        if h1 and isinstance(h1, Tag):
            title_text = h1.get_text(strip=True)
            if "." in title_text and title_text.split(".")[0].isdigit():
                data["title"] = title_text.split(".", 1)[1].strip()
            elif " - " in title_text:
                data["title"] = title_text.split(" - ", 1)[1].strip()
            else:
                data["title"] = title_text

        desc_header = soup.find("h2", id="description")
        if desc_header:
            parts = []
            for sib in desc_header.find_next_siblings():
                if not isinstance(sib, Tag) or sib.name == "h2":
                    break
                if sib.name == "p":
                    if sib.find("strong", class_="example"):
                        break
                    parts.append(sib.get_text(strip=True))
            data["problem_statement"] = "\n\n".join(parts)

        for strong in soup.find_all("strong", class_="example"):
            example_p = strong.parent
            if not example_p:
                continue
            pre = example_p.find_next("pre")
            if pre and isinstance(pre, Tag):
                example_text = pre.get_text(strip=True)
                data["examples"].append(example_text)
                if not data.get("example_input") and "Input:" in example_text:
                    try:
                        data["example_input"] = (
                            example_text.split("Input:")[1].split("Output:")[0].strip()
                        )
                        data["example_output"] = (
                            example_text.split("Output:")[1]
                            .split("Explanation:")[0]
                            .strip()
                        )
                    except Exception:
                        pass

        constraints_header = soup.find(
            lambda t: t.name == "p" and t.strong and "Constraints:" in t.get_text()
        )
        if constraints_header:
            ul = constraints_header.find_next("ul")
            if ul and isinstance(ul, Tag):
                for li in ul.find_all("li"):
                    data["constraints"].append(li.get_text(strip=True))

        # Complexity extraction from Solutions section if available
        solutions_section = soup.find("h2", id="solutions")
        if solutions_section:
            for sib in solutions_section.find_next_siblings():
                if not isinstance(sib, Tag) or sib.name == "h2":
                    break
                # Look for complexity notes in text
                text = sib.get_text()
                if "Time Complexity:" in text or "Time complexity:" in text:
                    data["optimal_time_complexity"] = (
                        text.split("Time complexity:")[1].split(".")[0].strip()
                    )
                if "Space Complexity:" in text or "Space complexity:" in text:
                    data["optimal_space_complexity"] = (
                        text.split("Space complexity:")[1].split(".")[0].strip()
                    )

        print(
            f"[PARSER_REPORT] {url} -> Title: {'OK' if data.get('title') else 'FAIL'}, Constraints: {len(data['constraints'])}, Examples: {len(data['examples'])}"
        )
        return data


def create_leetcode_scraper() -> LeetCodeScraper:
    return LeetCodeScraper()
