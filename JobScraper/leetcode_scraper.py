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

        # Static optimized prompt for Yellowcake
        self.yellowcake_prompt = """
Extract the following LeetCode problem details from the page content:
- leetcode_number (integer): The official LeetCode problem number (usually found in the title)
- title (string): The title of the problem
- difficulty (string): The difficulty level (Easy, Medium, or Hard)
- problem_statement (string): The full text of the problem description/description section
- examples (list of strings): Every example case provided (Input, Output, and optional Explanation)
- constraints (list of strings): Every individual constraint mentioned (e.g., "1 <= n <= 10^5")
- example_input (string): The 'Input' part of the very first example
- example_output (string): The 'Output' part of the very first example
- optimal_time_complexity (string): Based on constraints, what is the expected big-O time complexity?
- optimal_space_complexity (string): Based on constraints, what is the expected big-O space complexity?

Guidelines:
- Look for "Description" or "Problem Statement" for the main text.
- Look for "Example X:" labels and the text inside following <pre> tags.
- Look for "Constraints:" and the list items below it.
- If complexities aren't explicitly stated, infer them from typical LeetCode patterns for the given constraints.

Return a clean, valid JSON object with these exact keys.
"""

    async def _scrape_with_yellowcake(self, url: str, prompt: str) -> Any | None:
        """
        Scrape a URL using Yellowcake API.
        """
        if self.force_fallback:
            print("🚫 [YELLOWCAKE] Force fallback enabled. Bypassing API.")
            return None

        if (
            not self.yellowcake_api_key
            or self.yellowcake_api_key == "your_api_key_here"
        ):
            return None

        print(f"🍰 [YELLOWCAKE] Scraping {url}...")

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
        self, leetcode_number: int | None = None, problem_title: str | None = None
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

        print(f"🔍 Scraping leetcode.ca for {cache_key}...")

        try:
            # Scrape from leetcode.ca
            problem_data = await self._scrape_leetcode_ca(
                problem_number=leetcode_number, problem_title=problem_title
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
        self, problems: list[dict[str, str | int]], max_details: int = 10
    ) -> list[dict[str, Any]]:
        """
        Enrich problem metadata with full details.
        """
        enriched: list[dict[str, Any]] = []

        for i, problem in enumerate(problems[:max_details]):
            if i >= max_details:
                break

            number = problem.get("leetcode_number")
            title = problem.get("title")

            details = None
            if number is not None and isinstance(number, int):
                details = await self.get_problem_details(leetcode_number=number)
            elif title is not None and isinstance(title, str):
                details = await self.get_problem_details(problem_title=title)

            if details:
                enriched_problem = {**problem, **details}
                if "number" in details and "leetcode_number" not in enriched_problem:
                    enriched_problem["leetcode_number"] = details["number"]
                enriched.append(enriched_problem)
            else:
                enriched.append(problem)

        return enriched

    async def _fetch_company_csv(self, company_name: str) -> Optional[str]:
        """
        Fetch CSV from local directory using aggressive matching.
        1. Try exact/partial matches.
        2. Use LLM to resolve abbreviations/aliases (e.g. Royal Bank of Canada -> RBC).
        3. Use fuzzy matching as final fallback.
        """
        import difflib

        try:
            if not os.path.exists(self.data_dir):
                print(f"❌ Data directory missing: {self.data_dir}")
                return None

            # Get all company directories
            company_dirs = [
                d
                for d in os.listdir(self.data_dir)
                if os.path.isdir(os.path.join(self.data_dir, d))
            ]

            # 1. Aggressive local search with variations
            search_names = [
                company_name.lower(),
                company_name.lower().replace(" ", ""),
                re.sub(r"[^a-z0-9]", "", company_name.lower()),
            ]

            # Add potential abbreviation if it looks like one (e.g. "Royal Bank of Canada" -> "rbc")
            if " " in company_name:
                abbrev = "".join(
                    word[0] for word in company_name.split() if word
                ).lower()
                if len(abbrev) >= 2:
                    search_names.append(abbrev)

            matched_dir = None

            # Direct/Partial match loop
            for d in company_dirs:
                d_lower = d.lower().replace(" ", "")
                for target in search_names:
                    if target == d_lower or target in d_lower or d_lower in target:
                        matched_dir = d
                        break
                if matched_dir:
                    break

            # 2. LLM Resolution (if local search failed)
            if not matched_dir and settings.groq_api_key:
                print(f"🤖 Asking LLM to resolve company name: {company_name}")
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        prompt = f"Given a company name '{company_name}', return 3 potential directory names (short, common abbreviations, or legal names) that might represent it in a list of LeetCode company folders. Respond with only the names separated by commas. Example: 'Royal Bank of Canada' -> 'RBC, RoyalBank, RoyalBankofCanada'"
                        payload = {
                            "model": settings.groq_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                        }
                        headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
                        response = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                        if response.status_code == 200:
                            content = response.json()["choices"][0]["message"][
                                "content"
                            ]
                            variations = [v.strip().lower() for v in content.split(",")]
                            print(f"💡 LLM suggests variations: {variations}")
                            for d in company_dirs:
                                d_clean = d.lower().replace(" ", "")
                                if any(
                                    v in d_clean or d_clean in v for v in variations
                                ):
                                    matched_dir = d
                                    break
                except Exception as e:
                    print(f"⚠️ LLM resolution failed: {e}")

            # 3. Fuzzy matching fallback
            if not matched_dir:
                matches = difflib.get_close_matches(
                    company_name, company_dirs, n=1, cutoff=0.5
                )
                if matches:
                    matched_dir = matches[0]
                    print(f"🎯 Fuzzy match selected: {matched_dir}")

            if matched_dir:
                dir_path = os.path.join(self.data_dir, matched_dir)
                files = os.listdir(dir_path)
                # Priority: All.csv, then any CSV containing "all"
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

            print(f"⚠️ No CSV folder found for {company_name}")
            return None
        except Exception as e:
            print(f"❌ Local CSV error: {e}")
            return None

            # Get all company directories
            company_dirs = [
                d
                for d in os.listdir(self.data_dir)
                if os.path.isdir(os.path.join(self.data_dir, d))
            ]

            # 1. Aggressive local search with variations
            search_names = [
                company_name.lower(),
                company_name.lower().replace(" ", ""),
                re.sub(r"[^a-z0-9]", "", company_name.lower()),
            ]

            # Add potential abbreviation if it looks like one (e.g. "Royal Bank of Canada" -> "rbc")
            if " " in company_name:
                abbrev = "".join(
                    word[0] for word in company_name.split() if word
                ).lower()
                if len(abbrev) >= 2:
                    search_names.append(abbrev)

            matched_dir = None

            # Direct/Partial match loop
            for d in company_dirs:
                d_lower = d.lower().replace(" ", "")
                for target in search_names:
                    if target == d_lower or target in d_lower or d_lower in target:
                        matched_dir = d
                        break
                if matched_dir:
                    break

            # 2. LLM Resolution (if local search failed)
            if not matched_dir and settings.groq_api_key:
                print(f"🤖 Asking LLM to resolve company name: {company_name}")
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        prompt = f"Given a company name '{company_name}', return 3 potential directory names (short, common abbreviations, or legal names) that might represent it in a list of LeetCode company folders. Respond with only the names separated by commas. Example: 'Royal Bank of Canada' -> 'RBC, RoyalBank, RoyalBankofCanada'"
                        payload = {
                            "model": settings.groq_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                        }
                        headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
                        response = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                        if response.status_code == 200:
                            content = response.json()["choices"][0]["message"][
                                "content"
                            ]
                            variations = [v.strip().lower() for v in content.split(",")]
                            print(f"💡 LLM suggests variations: {variations}")
                            for d in company_dirs:
                                d_clean = d.lower().replace(" ", "")
                                if any(
                                    v in d_clean or d_clean in v for v in variations
                                ):
                                    matched_dir = d
                                    break
                except Exception as e:
                    print(f"⚠️ LLM resolution failed: {e}")

            # 3. Fuzzy matching fallback
            if not matched_dir:
                matches = difflib.get_close_matches(
                    company_name, company_dirs, n=1, cutoff=0.5
                )
                if matches:
                    matched_dir = matches[0]
                    print(f"🎯 Fuzzy match selected: {matched_dir}")

            if matched_dir:
                dir_path = os.path.join(self.data_dir, matched_dir)
                files = os.listdir(dir_path)
                # Priority: All.csv, then any CSV containing "all"
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

            print(f"⚠️ No CSV folder found for {company_name}")
            return None
        except Exception as e:
            print(f"❌ Local CSV error: {e}")
            return None

    def _parse_csv_data(self, csv_text: str) -> list[dict[str, str | int]]:
        """
        Parse CSV metadata.
        """
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

    async def _scrape_leetcode_ca(
        self, problem_number: int | None = None, problem_title: str | None = None
    ) -> dict[str, Any] | None:
        """
        Discovers the specific problem URL on leetcode.ca by searching the index page,
        then uses Yellowcake to extract structured data from that specific link.
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                problem_link: Optional[str] = None

                # 1. DISCOVERY: Go to leetcode.ca and find the link by searching inner text
                print(
                    f"🔍 Discovery: Fetching leetcode.ca index to find problem {problem_number or problem_title}..."
                )

                resp = await client.get(self.leetcode_ca_base)
                if resp.status_code != 200:
                    print(f"❌ Failed to load leetcode.ca index: {resp.status_code}")
                    return None

                soup = BeautifulSoup(resp.text, "lxml")

                # We search for the <a> tag where the inner text contains the problem number
                target_found = False
                for link in soup.find_all("a"):
                    if not isinstance(link, Tag):
                        continue

                    inner_text = link.get_text(strip=True)

                    # Logic: Check if the number (e.g., "3768") is in the inner text
                    if problem_number:
                        num_str = str(problem_number)
                        # We look for the number as a standalone word or at the start of the text
                        # e.g. "3768. Title" or "3768 - Title"
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
                            problem_link = href
                            if not problem_link.startswith("http"):
                                problem_link = f"{self.leetcode_ca_base.rstrip('/')}/{problem_link.lstrip('/')}"
                            print(f"🎯 Found link via inner text: {problem_link}")
                            break

                if not problem_link:
                    print(
                        f"⚠️ Discovery failed: No <a> tag found containing '{problem_number or problem_title}' in text."
                    )
                    return None

                # 2. EXTRACTION: Pass the verified URL to Yellowcake
                if self.yellowcake_api_key:
                    print(
                        f"🍰 Yellowcake: Extracting from verified URL: {problem_link}"
                    )
                    data = await self._scrape_with_yellowcake(
                        problem_link, self.yellowcake_prompt
                    )

                    if data and isinstance(data, dict):
                        return {
                            "leetcode_number": data.get("leetcode_number")
                            or problem_number,
                            "title": data.get("title") or problem_title,
                            "difficulty": data.get("difficulty") or "medium",
                            "problem_statement": data.get("problem_statement"),
                            "examples": data.get("examples") or [],
                            "constraints": data.get("constraints") or [],
                            "example_input": data.get("example_input"),
                            "example_output": data.get("example_output"),
                            "optimal_time_complexity": data.get(
                                "optimal_time_complexity"
                            ),
                            "optimal_space_complexity": data.get(
                                "optimal_space_complexity"
                            ),
                            "url": problem_link,
                        }

                # 3. FALLBACK: Manual BS4 parsing
                print(f"🐚 Fallback: Manual scrape of {problem_link}")
                resp = await client.get(problem_link)
                if resp.status_code == 200:
                    return self._parse_leetcode_page(
                        resp.text, problem_number, problem_link
                    )

                return None
            except Exception as e:
                print(f"❌ Error in _scrape_leetcode_ca: {e}")
                return None

    def _parse_leetcode_page(
        self, html: str, number: int | None, url: str
    ) -> dict[str, Any]:
        """Manual parsing fallback based on leetcode.ca HTML structure."""
        soup = BeautifulSoup(html, "lxml")
        data: dict[str, Any] = {
            "url": url,
            "leetcode_number": number,
            "examples": [],
            "constraints": [],
            "problem_statement": "",
            "difficulty": "medium",  # Default if not found
        }

        # 1. Extract Title
        h1 = soup.find("h1")
        if h1 and isinstance(h1, Tag):
            title_text = h1.get_text(strip=True)
            # Remove problem number prefix if present (e.g., "3000. Title")
            if "." in title_text and title_text.split(".")[0].isdigit():
                data["title"] = title_text.split(".", 1)[1].strip()
            elif " - " in title_text:
                data["title"] = title_text.split(" - ", 1)[1].strip()
            else:
                data["title"] = title_text

        # 2. Extract Description / Problem Statement
        # On leetcode.ca, description usually follows an h2 with id="description"
        desc_header = soup.find("h2", id="description")
        if desc_header:
            statement_parts = []
            for sibling in desc_header.find_next_siblings():
                if not isinstance(sibling, Tag):
                    continue
                if sibling.name == "h2":  # Stop at next section (usually Solutions)
                    break
                if sibling.name == "p":
                    # Check if we hit examples
                    if sibling.find("strong", class_="example"):
                        break
                    statement_parts.append(sibling.get_text(strip=True))
            data["problem_statement"] = "\n\n".join(statement_parts)

        # 3. Extract Examples
        # Examples are often in <p><strong>Example X:</strong></p> followed by <pre>
        for strong in soup.find_all("strong", class_="example"):
            example_p = strong.parent
            if not example_p:
                continue

            # Find the following <pre> block
            pre = example_p.find_next("pre")
            if pre and isinstance(pre, Tag):
                example_text = pre.get_text(strip=True)
                data["examples"].append(example_text)

                # Try to extract input/output for first example
                if not data.get("example_input") and "Input:" in example_text:
                    try:
                        # Extract between "Input:" and "Output:"
                        input_part = (
                            example_text.split("Input:")[1].split("Output:")[0].strip()
                        )
                        data["example_input"] = input_part
                        output_part = (
                            example_text.split("Output:")[1]
                            .split("Explanation:")[0]
                            .strip()
                        )
                        data["example_output"] = output_part
                    except Exception:
                        pass

        # 4. Extract Constraints
        # Usually starts with a <p><strong>Constraints:</strong></p> followed by <ul>
        constraints_header = soup.find(
            lambda t: t.name == "p" and t.strong and "Constraints:" in t.get_text()
        )
        if constraints_header:
            ul = constraints_header.find_next("ul")
            if ul and isinstance(ul, Tag):
                for li in ul.find_all("li"):
                    data["constraints"].append(li.get_text(strip=True))

        return data


def create_leetcode_scraper() -> LeetCodeScraper:
    return LeetCodeScraper()
