"""
LeetCode Company Problems Scraper

Scrapes company-specific LeetCode problems from:
1. GitHub repo: liquidslr/leetcode-company-wise-problems
2. LeetCode.ca for actual problem content

Architecture: Modular and swappable for Yellowcake integration later.
Uses file-based caching to avoid duplicate scraping.

Data Flow:
1. Fetch company CSV from GitHub repo
2. Parse CSV to get LeetCode question numbers
3. For each question, scrape leetcode.ca/<number>
4. Extract problem details (title, description, difficulty, examples)
5. Cache everything to avoid re-scraping
"""

from __future__ import annotations

import csv
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from cache import get_cache


class LeetCodeScraper:
    """
    Scrape company-specific LeetCode problems.

    Modular interface allows swapping with Yellowcake later:
    - All methods have clear contracts
    - Caching is built-in
    - Can be replaced with YellowcakeScraperAdapter
    """

    def __init__(self) -> None:
        self.cache = get_cache()
        self.github_base = "https://raw.githubusercontent.com/liquidslr/leetcode-company-wise-problems/main"
        self.leetcode_ca_base = "https://leetcode.ca"

    async def get_company_problems(
        self, company_name: str, limit: int = 20
    ) -> list[dict[str, str | int]]:
        """
        Get LeetCode problems asked by a specific company.

        Args:
            company_name: Company name (e.g., 'Google', 'Amazon', 'Meta')
            limit: Maximum number of problems to return

        Returns:
            List of problem metadata: [{
                "leetcode_number": 1,
                "title": "Two Sum",
                "difficulty": "easy",
                "link": "https://leetcode.com/problems/two-sum",
                "frequency": "high"
            }]
        """
        # Check cache first
        cached = self.cache.get_scraped_data(
            company=company_name, source="leetcode_problems"
        )

        if cached:
            print(f"✅ Cache hit for {company_name} LeetCode problems")
            return cached[:limit]  # type: ignore[return-value]

        print(f"🔍 Fetching {company_name} LeetCode problems from GitHub...")

        try:
            # Find the company's CSV file in the GitHub repo
            csv_data = await self._fetch_company_csv(company_name)

            if not csv_data:
                print(f"⚠️ No LeetCode data found for {company_name}")
                return []

            # Parse CSV and extract problem metadata
            problems = self._parse_csv_data(csv_data)

            # Cache the results
            self.cache.set_scraped_data(
                company=company_name, source="leetcode_problems", data=problems
            )

            return problems[:limit]

        except Exception as e:
            print(f"❌ Error fetching LeetCode problems: {e}")
            return []

    async def get_problem_details(
        self, leetcode_number: int | None = None, problem_title: str | None = None
    ) -> dict[str, str | list[str] | int | None] | None:
        """
        Get full problem details from leetcode.ca.

        Args:
            leetcode_number: LeetCode problem number (if known)
            problem_title: Problem title (if number unknown)

        Returns:
            Problem details: {
                "number": 1,
                "title": "Two Sum",
                "difficulty": "easy",
                "description": "Given an array...",
                "examples": ["Example 1: ...", "Example 2: ..."],
                "constraints": ["1 <= nums.length <= 10^4", ...],
                "url": "https://leetcode.ca/2015-12-18-1-Two-Sum/"
            }
        """
        cache_key = (
            str(leetcode_number) if leetcode_number else (problem_title or "unknown")
        )

        # Check cache
        cached = self.cache.get_scraped_data(
            company="leetcode", source="problem_details", url=cache_key
        )

        if cached:
            return cached  # type: ignore[return-value]

        print(
            f"🔍 Scraping LeetCode problem from leetcode.ca (number={leetcode_number}, title={problem_title})..."
        )

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
    ) -> list[dict[str, str | int | list[str]]]:
        """
        Enrich problem metadata with full details from leetcode.ca.

        Args:
            problems: List of problem metadata from get_company_problems()
            max_details: Maximum number of problems to enrich (avoid too many requests)

        Returns:
            Enriched problems with full descriptions, examples, etc.
        """
        enriched = []

        for i, problem in enumerate(problems[:max_details]):
            if i >= max_details:
                break

            number = problem.get("leetcode_number")
            title = problem.get("title")

            # Get full details (try with number first, then title)
            details = None
            if number is not None and isinstance(number, int):
                details = await self.get_problem_details(leetcode_number=number)
            elif title is not None and isinstance(title, str):
                details = await self.get_problem_details(problem_title=title)

            if details:
                # Merge metadata with details
                enriched_problem = {**problem, **details}
                # Ensure leetcode_number is set if we got it from scraping
                if "number" in details and "leetcode_number" not in enriched_problem:
                    enriched_problem["leetcode_number"] = details["number"]
                enriched.append(enriched_problem)
            else:
                # Keep original metadata even if scraping fails
                enriched.append(problem)

        return enriched

    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================

    async def _fetch_company_csv(self, company_name: str) -> Optional[str]:
        """
        Fetch the company's CSV file from GitHub.

        CSV naming pattern in repo:
        - companies/<CompanyName>All.csv
        - e.g., GoogleAll.csv, AmazonAll.csv, MetaAll.csv
        """
        # Try different name variations
        variations = [
            company_name,  # Google
            company_name.replace(" ", ""),  # JPMorgan Chase -> JPMorganChase
            company_name.split()[0],  # "Bank of America" -> Bank
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for variant in variations:
                # Try with "All" suffix (most common)
                csv_url = f"{self.github_base}/companies/{variant}All.csv"

                try:
                    response = await client.get(csv_url)

                    if response.status_code == 200:
                        print(f"✅ Found CSV at {csv_url}")
                        return response.text

                except Exception:
                    continue

        return None

    def _parse_csv_data(self, csv_text: str) -> list[dict[str, str | int]]:
        """
        Parse CSV data to extract problem metadata.

        Expected CSV columns (from liquidslr/leetcode-company-wise-problems):
        - ID (problem number)
        - Title
        - Acceptance
        - Difficulty
        - Frequency-something
        - Link (to LeetCode problem)
        """
        problems = []

        lines = csv_text.strip().split("\n")
        if not lines:
            return []

        # Parse CSV
        reader = csv.DictReader(lines)

        for row in reader:
            try:
                # Extract relevant fields
                problem = {}

                # Problem number (from ID or Link)
                if "ID" in row and row["ID"].strip():
                    try:
                        problem["leetcode_number"] = int(row["ID"].strip())
                    except (ValueError, TypeError):
                        pass

                # Try to extract from Link URL if no ID
                if "leetcode_number" not in problem and "Link" in row and row["Link"]:
                    link = row["Link"]
                    # Some CSVs have problem numbers in the URL path
                    # Format: https://leetcode.com/problems/two-sum/ (number is 1)
                    # We can't get number from slug alone, but we'll try to get it when scraping
                    # Store the link for later use
                    problem["link"] = link

                # Title
                if "Title" in row:
                    problem["title"] = row["Title"]

                # Difficulty
                if "Difficulty" in row:
                    problem["difficulty"] = row["Difficulty"].lower()

                # Link (if not already set)
                if "link" not in problem and "Link" in row:
                    problem["link"] = row["Link"]

                # Frequency (if available)
                freq_cols = [k for k in row.keys() if "frequency" in k.lower()]
                if freq_cols:
                    try:
                        freq_val = float(row[freq_cols[0]])
                        if freq_val > 0.7:
                            problem["frequency"] = "very_common"
                        elif freq_val > 0.4:
                            problem["frequency"] = "common"
                        elif freq_val > 0.2:
                            problem["frequency"] = "occasional"
                        else:
                            problem["frequency"] = "rare"
                    except (ValueError, KeyError):
                        problem["frequency"] = "unknown"

                # If we have a link but no ID, try to extract problem number from URL
                if "link" in problem and "leetcode_number" not in problem:
                    # Try to extract from URL slug or title
                    # Some CSVs have problem numbers in the title or we can infer from order
                    # For now, we'll try to get it from leetcode.ca when we scrape
                    pass

                # Only add if we have at least title (difficulty is nice but not required)
                if "title" in problem:
                    # If no leetcode_number, we'll try to find it when scraping leetcode.ca
                    # If no difficulty, we'll try to infer it or leave it as None
                    if "difficulty" not in problem:
                        problem["difficulty"] = "medium"  # Default
                    problems.append(problem)

            except Exception as e:
                print(f"Warning: Failed to parse CSV row: {e}")
                continue

        return problems

    async def _scrape_leetcode_ca(
        self, problem_number: int | None = None, problem_title: str | None = None
    ) -> dict[str, str | list[str] | int | None] | None:
        """
        Scrape problem details from leetcode.ca.

        LeetCode.ca URL pattern (from example):
        - Problem pages: leetcode.ca/YYYY-MM-DD-NUMBER-Title/
        - Example: leetcode.ca/2024-01-15-3000-Maximum-Area-of-Longest-Diagonal-Rectangle/
        - All problems listing: leetcode.ca/all/problems.html

        Args:
            problem_number: LeetCode problem number (if known)
            problem_title: Problem title to search for (if number unknown)
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                problem_link = None

                # Strategy 1: If we have problem number, try to find it in the all problems page
                if problem_number:
                    # Fetch the all problems page
                    response = await client.get(
                        f"{self.leetcode_ca_base}/all/problems.html"
                    )

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "lxml")

                        # Find link containing the problem number
                        # Links might be in format: /2024-01-15-3000-Title/ or just contain "3000"
                        for link in soup.find_all("a", href=True):
                            href = link.get("href")
                            if not isinstance(href, str):
                                continue
                            text = link.get_text()

                            # Check if link or text contains problem number
                            if (
                                str(problem_number) in href
                                or str(problem_number) in text
                            ):
                                # Verify it's a problem link (not a category link)
                                if (
                                    "/20" in href
                                    or "problem" in href.lower()
                                    or any(char.isdigit() for char in href)
                                ):
                                    problem_link = href
                                    break

                # Strategy 2: If we have title, search for it
                if not problem_link and problem_title:
                    response = await client.get(
                        f"{self.leetcode_ca_base}/all/problems.html"
                    )
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "lxml")
                        # Normalize title for matching
                        title_words = set(
                            word.lower()
                            for word in problem_title.split()
                            if len(word) > 3
                        )

                        for link in soup.find_all("a", href=True):
                            text = link.get_text().lower()
                            href = link.get("href")
                            if not isinstance(href, str):
                                continue

                            # Check if significant words from title match
                            if title_words and any(
                                word in text for word in title_words
                            ):
                                if "/20" in href or "problem" in href.lower():
                                    problem_link = href
                                    break

                # Strategy 3: Try constructing URL directly if we have number
                # Format: /YYYY-MM-DD-NUMBER-Title/ (we don't know exact date, so skip this)

                if not problem_link:
                    print(
                        f"⚠️ Could not find problem on leetcode.ca (number={problem_number}, title={problem_title})"
                    )
                    return None

                # Make sure link is absolute
                if not problem_link.startswith("http"):
                    if problem_link.startswith("/"):
                        problem_link = f"{self.leetcode_ca_base}{problem_link}"
                    else:
                        problem_link = f"{self.leetcode_ca_base}/{problem_link}"

                # Now scrape the actual problem page
                prob_response = await client.get(problem_link)

                if prob_response.status_code != 200:
                    print(
                        f"⚠️ Failed to fetch problem page: {problem_link} (status: {prob_response.status_code})"
                    )
                    return None

                # Extract problem number from page if not provided
                actual_number = problem_number
                if not actual_number:
                    soup = BeautifulSoup(prob_response.text, "lxml")
                    h1 = soup.find("h1")
                    if h1:
                        h1_text = h1.get_text()
                        # Format: "3000 - Title" or "3000. Title"
                        if " - " in h1_text:
                            try:
                                actual_number = int(h1_text.split(" - ")[0].strip())
                            except ValueError:
                                pass
                        elif ". " in h1_text and h1_text[0].isdigit():
                            try:
                                actual_number = int(h1_text.split(". ")[0].strip())
                            except ValueError:
                                pass

                return self._parse_leetcode_page(
                    prob_response.text, actual_number, problem_link
                )

            except Exception as e:
                print(f"Error scraping leetcode.ca: {e}")
                import traceback

                traceback.print_exc()
                return None

    def _parse_leetcode_page(
        self, html: str, number: int | None, url: str
    ) -> dict[str, str | list[str] | int | None]:
        """
        Parse LeetCode.ca problem page HTML.

        Based on example_leetcode.ca structure:
        - <h1> contains "NUMBER - Title" or link to leetcode.com
        - <h2 id="description"> for problem description
        - Examples in <pre> tags after "Example X:" headings
        - Constraints in <ul> tags after "Constraints:" heading
        """
        soup = BeautifulSoup(html, "lxml")

        problem_data: dict[str, str | list[str] | int | None] = {"url": url}

        if number:
            problem_data["leetcode_number"] = number

        # Extract title from <h1> - format: "3000 - Maximum Area of Longest Diagonal Rectangle"
        # Or: <h1><a href="...">3000. Maximum Area...</a></h1>
        h1 = soup.find("h1")
        if h1:
            # Check if there's a link inside
            h1_link = h1.find("a")
            if h1_link:
                title_text = h1_link.get_text(strip=True)
            else:
                title_text = h1.get_text(strip=True)

            # Format: "3000 - Maximum Area..." or "3000. Maximum Area..."
            if " - " in title_text:
                parts = title_text.split(" - ", 1)
                if not number and parts[0].strip().isdigit():
                    problem_data["leetcode_number"] = int(parts[0].strip())
                problem_data["title"] = (
                    parts[1].strip() if len(parts) > 1 else title_text
                )
            elif ". " in title_text and title_text[0].isdigit():
                # Format: "3000. Maximum Area..."
                parts = title_text.split(". ", 1)
                if not number and parts[0].strip().isdigit():
                    problem_data["leetcode_number"] = int(parts[0].strip())
                problem_data["title"] = (
                    parts[1].strip() if len(parts) > 1 else title_text
                )
            else:
                problem_data["title"] = title_text.strip()

        # Extract description - look for <h2 id="description"> or just Description section
        desc_text = ""
        desc_heading = soup.find("h2", id="description")
        if not desc_heading:
            # Try finding by text
            for h2 in soup.find_all("h2"):
                if "description" in h2.get_text().lower():
                    desc_heading = h2
                    break

        if desc_heading:
            # Get all content after description heading until next h2
            description_parts = []
            for sibling in desc_heading.find_next_siblings():
                if sibling.name == "h2":
                    break
                if sibling.name == "p":
                    description_parts.append(sibling.get_text(strip=True))
                elif sibling.name in ["div", "section"]:
                    # Get text from nested elements
                    text = sibling.get_text(separator="\n", strip=True)
                    if text:
                        description_parts.append(text)

            desc_text = "\n\n".join(description_parts)

        # If no description section found, try to get from article content
        if not desc_text:
            article = soup.find("article") or soup.find(
                "div",
                class_=lambda x: x is not None
                and isinstance(x, str)
                and "post" in x.lower(),
            )
            if article:
                # Get all paragraphs before "Example" or "Constraints"
                desc_parts = []
                for elem in article.find_all(["p", "div"]):
                    text = elem.get_text(strip=True)
                    if text and not any(
                        keyword in text.lower()
                        for keyword in ["example", "constraint", "solution"]
                    ):
                        if len(text) > 20:  # Filter out short fragments
                            desc_parts.append(text)
                    if "example" in text.lower() or "constraint" in text.lower():
                        break
                desc_text = "\n\n".join(desc_parts[:10])  # Limit to first 10 paragraphs

        if desc_text:
            problem_data["problem_statement"] = desc_text[:5000]  # Limit length

        # Extract examples from <pre> tags or Example sections
        examples = []
        example_inputs = []
        example_outputs = []

        # Look for Example sections
        for elem in soup.find_all(["h2", "h3", "strong", "p"]):
            text = elem.get_text()
            if "example" in text.lower() and (
                "input" in text.lower() or "output" in text.lower()
            ):
                # Find the <pre> tag after this
                pre = elem.find_next("pre")
                if pre:
                    example_text = pre.get_text(strip=True)
                    examples.append(example_text)

                    # Try to extract input/output separately
                    if "input" in text.lower():
                        example_inputs.append(example_text)
                    if "output" in text.lower():
                        example_outputs.append(example_text)

        # Fallback: get all <pre> tags
        if not examples:
            for pre in soup.find_all("pre"):
                example_text = pre.get_text(strip=True)
                # Filter out code solutions
                if (
                    "class Solution" not in example_text
                    and "def " not in example_text[:50]
                ):
                    if len(example_text) > 10:
                        examples.append(example_text)

        if examples:
            problem_data["examples"] = examples[:5]  # Limit to 5 examples
        if example_inputs:
            problem_data["example_input"] = (
                example_inputs[0] if example_inputs else None
            )
        if example_outputs:
            problem_data["example_output"] = (
                example_outputs[0] if example_outputs else None
            )

        # Extract constraints from <ul> tags after "Constraints:" heading
        constraints = []
        constraints_heading = None
        for elem in soup.find_all(["h2", "h3", "strong", "p"]):
            text = elem.get_text()
            if "constraint" in text.lower():
                constraints_heading = elem
                break

        if constraints_heading:
            # Find <ul> after constraints heading
            ul = constraints_heading.find_next("ul")
            if ul:
                for li in ul.find_all("li"):
                    constraint_text = li.get_text(strip=True)
                    if constraint_text:
                        constraints.append(constraint_text)

        # Fallback: find any <ul> with constraint-like content
        if not constraints:
            for ul in soup.find_all("ul"):
                for li in ul.find_all("li"):
                    constraint_text = li.get_text(strip=True)
                    if any(
                        char in constraint_text
                        for char in ["<=", ">=", "<", ">", "1 <="]
                    ):
                        constraints.append(constraint_text)

        if constraints:
            problem_data["constraints"] = constraints

        return problem_data


# ============================================================================
# FACTORY FUNCTION (for easy swapping with Yellowcake later)
# ============================================================================


def create_leetcode_scraper() -> LeetCodeScraper:
    """
    Factory function to create LeetCode scraper.

    Later this can be swapped to:
        return YellowcakeScraperAdapter()

    Which would implement the same interface but use Yellowcake API.
    """
    return LeetCodeScraper()
