"""
Scraping engine for JobScraper.
Handles raw data extraction from Job Postings, Glassdoor, and Company Info.
"""

from __future__ import annotations
import json
import httpx
import asyncio
from bs4 import BeautifulSoup
from config import settings


class ScraperEngine:
    """
    Handles the heavy lifting of scraping web content.
    Integrated with Yellowcake and Playwright.
    """

    def __init__(self, leetcode_scraper: Any) -> None:
        self.leetcode_scraper = leetcode_scraper

    async def scrape_job_posting(self, url: str) -> dict[str, Any] | None:
        """Scrapes job postings with Yellowcake or Playwright fallback."""
        if settings.yellowcake_api_key and settings.yellowcake_api_key != "mock":
            print(f"🍰 [YELLOWCAKE] Scraping job posting: {url}")
            prompt = "Extract all text from this job posting: title, location, description, requirements, and responsibilities."
            content = await self.leetcode_scraper._scrape_with_yellowcake(url, prompt)
            if content:
                return {"full_content": str(content), "url": url}

        print(f"🎭 [PLAYWRIGHT] Scraping job posting: {url}")
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"⚠️ [PLAYWRIGHT] Timeout or load error: {e}")

                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                # Remove junk
                for s in soup(
                    [
                        "script",
                        "style",
                        "nav",
                        "footer",
                        "header",
                        "button",
                        "svg",
                        "iframe",
                    ]
                ):
                    s.decompose()

                text = soup.get_text(separator="\n", strip=True)
                await browser.close()

                if len(text) > 300:
                    print(f"✅ [PLAYWRIGHT] Success: {len(text)} chars")
                    return {"full_content": text[:25000], "url": url}
        except Exception as e:
            print(f"❌ Playwright Failed: {e}")

        return None

    async def scrape_glassdoor_interviews(self, company: str) -> dict[str, Any] | None:
        """Scrapes Glassdoor interview reviews."""
        search_url = f"https://www.glassdoor.com/Interview/{company.replace(' ', '-')}-interview-questions-SRCH_KE0,{len(company)}.htm"
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(search_url, headers=headers)
                soup = BeautifulSoup(resp.text, "lxml")
                interviews = [
                    e.get_text(strip=True)[:1000]
                    for e in soup.find_all(["div", "article"])
                    if len(e.get_text()) > 150
                ][:10]
                return {"interviews": interviews, "url": search_url}
        except Exception as e:
            print(f"⚠️ Glassdoor Scrape Failed: {e}")
            return None

    async def scrape_company_info(self, company: str) -> dict[str, Any] | None:
        """Basic company info research via search engines."""
        url = f"https://www.google.com/search?q={company}+about+culture+mission"
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, "lxml")
                res = [
                    e.get_text()[:500]
                    for e in soup.find_all(["div", "p"])
                    if company.lower() in e.get_text().lower()
                ][:8]
                return {"info": res, "url": url}
        except Exception as e:
            print(f"⚠️ Company Info Scrape Failed: {e}")
            return None
