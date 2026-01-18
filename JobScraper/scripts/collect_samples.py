"""
Script to collect 25 sample LeetCode problem HTML pages for prompt optimization.
Reuses logic from leetcode_scraper.py.
"""

import os
import random
import asyncio
import httpx
from bs4 import BeautifulSoup, Tag
import sys

# Mock settings before importing leetcode_scraper
os.environ["YELLOWCAKE_API_KEY"] = "mock"
os.environ["GROQ_API_KEY"] = "mock"

# Add JobScraper to path
sys.path.append(os.path.join(os.getcwd(), "JobScraper"))

from leetcode_scraper import LeetCodeScraper


async def collect_samples():
    scraper = LeetCodeScraper()
    output_dir = "JobScraper/data/optimization/leetcode_samples"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Get problem numbers from local CSVs
    print(f"🔍 Searching for sample problems in {scraper.data_dir}...")

    problem_identifiers = []  # List of (number, title) tuples
    all_csvs = []
    for root, dirs, files in os.walk(scraper.data_dir):
        for file in files:
            if file.endswith(".csv"):
                all_csvs.append(os.path.join(root, file))

    if not all_csvs:
        print("❌ No CSV files found!")
        return

    random.shuffle(all_csvs)
    for csv_path in all_csvs:
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                import csv

                reader = csv.DictReader(f)
                for row in reader:
                    num = None
                    title = row.get("Title")
                    if "ID" in row and row["ID"].strip().isdigit():
                        num = int(row["ID"].strip())

                    if num or title:
                        problem_identifiers.append((num, title))

                    if len(problem_identifiers) >= 200:
                        break
        except Exception:
            continue
        if len(problem_identifiers) >= 200:
            break

    if not problem_identifiers:
        print("❌ No problems found in CSVs!")
        return

    samples = random.sample(problem_identifiers, min(5, len(problem_identifiers)))
    print(f"🎯 Selected {len(samples)} problems to collect.")

    # 2. Use LeetCodeScraper.discover_problem_link to find the actual URLs
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for num, title in samples:
            print(f"🌐 Discovering URL for problem {num or title}...")
            try:
                problem_link = await scraper.discover_problem_link(
                    problem_number=num, problem_title=title
                )

                if problem_link:
                    print(f"✅ Found link: {problem_link}. Fetching HTML...")
                    p_resp = await client.get(problem_link)
                    if p_resp.status_code == 200:
                        filename = (
                            f"{num}.html" if num else f"{title.replace(' ', '_')}.html"
                        )
                        file_path = os.path.join(output_dir, filename)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(p_resp.text)
                        print(f"💾 Saved {filename}")
                    else:
                        print(
                            f"❌ Failed to fetch {problem_link} (Status: {p_resp.status_code})"
                        )
                else:
                    print(f"⚠️ Could not discover link for problem {num or title}")
            except Exception as e:
                print(f"❌ Error collecting {num or title}: {e}")


if __name__ == "__main__":
    asyncio.run(collect_samples())
