"""
Caching layer for JobScraper to avoid duplicate scraping and LLM calls.
Saves API credits and improves response times.

Cache Strategy:
- Scraping cache: keyed by (company_name, source_type, url_hash)
- LLM cache: keyed by (prompt_hash, model_name)
- File-based JSON storage in .cache/ directory
- TTL-based expiration (default 7 days)
"""

from __future__ import annotations
import json
import hashlib
import time
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta
from config import settings


class CacheManager:
    """
    Simple file-based cache manager with TTL support.

    Cache Structure:
    .cache/
        scraping/
            <company>_<source>_<hash>.json
        llm/
            <prompt_hash>_<model>.json
        stats.json
    """

    def __init__(self, cache_dir: str = ".cache", default_ttl_days: int = 7) -> None:
        self.cache_dir = Path(cache_dir)
        self.default_ttl = timedelta(days=default_ttl_days)
        self.debug_mode = settings.debug

        # Create cache directories
        self.scraping_dir = self.cache_dir / "scraping"
        self.llm_dir = self.cache_dir / "llm"
        self.scraping_dir.mkdir(parents=True, exist_ok=True)
        self.llm_dir.mkdir(parents=True, exist_ok=True)

        # Stats tracking
        self.stats_file = self.cache_dir / "stats.json"
        self.stats = self._load_stats()

    def _load_stats(self) -> dict[str, Any]:
        """Load cache statistics."""
        if self.stats_file.exists():
            with open(self.stats_file, "r") as f:
                return json.load(f)
        return {
            "scraping_hits": 0,
            "scraping_misses": 0,
            "llm_hits": 0,
            "llm_misses": 0,
            "total_api_calls_saved": 0,
            "estimated_credits_saved": 0.0,
        }

    def _save_stats(self) -> None:
        """Save cache statistics."""
        with open(self.stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

    def _hash_string(self, text: str) -> str:
        """Generate SHA256 hash of a string."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _is_expired(self, cache_data: dict[str, Any]) -> bool:
        """Check if cached data has expired."""
        if "cached_at" not in cache_data:
            return True

        cached_time = datetime.fromisoformat(cache_data["cached_at"])
        expiry = cached_time + self.default_ttl
        return datetime.now() > expiry

    # ========================================================================
    # SCRAPING CACHE
    # ========================================================================

    def get_scraped_data(
        self, company: str, source: str, url: Optional[str] = None
    ) -> Any:
        """
        Retrieve cached scraped data.

        Args:
            company: Company name
            source: Source type (e.g., 'glassdoor', 'job_posting', 'leetcode')
            url: Optional URL for more specific caching

        Returns:
            Cached data if found and not expired, else None
        """
        if self.debug_mode:
            print("⚠️ Debug mode: Cache skipped")
            return None

        cache_key = self._make_scraping_key(company, source, url)
        cache_file = self.scraping_dir / f"{cache_key}.json"

        if not cache_file.exists():
            self.stats["scraping_misses"] += 1
            self._save_stats()
            return None

        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)

            if self._is_expired(cache_data):
                # Expired - delete and return None
                cache_file.unlink()
                self.stats["scraping_misses"] += 1
                self._save_stats()
                return None

            # Cache hit!
            self.stats["scraping_hits"] += 1
            self.stats["total_api_calls_saved"] += 1
            self._save_stats()

            return cache_data.get("data")

        except Exception as e:
            print(f"Cache read error: {e}")
            return None

    def set_scraped_data(
        self, company: str, source: str, data: Any, url: Optional[str] = None
    ) -> None:
        """
        Store scraped data in cache.

        Args:
            company: Company name
            source: Source type
            data: Data to cache (can be dict, list, or any JSON-serializable type)
            url: Optional URL
        """
        cache_key = self._make_scraping_key(company, source, url)
        cache_file = self.scraping_dir / f"{cache_key}.json"

        cache_entry = {
            "company": company,
            "source": source,
            "url": url,
            "cached_at": datetime.now().isoformat(),
            "data": data,
        }

        try:
            with open(cache_file, "w") as f:
                json.dump(cache_entry, f, indent=2)
        except Exception as e:
            print(f"Cache write error: {e}")

    def _make_scraping_key(self, company: str, source: str, url: Optional[str]) -> str:
        """Generate cache key for scraped data."""
        company_clean = company.lower().replace(" ", "_").replace("/", "_")
        source_clean = source.lower().replace(" ", "_")

        if url:
            url_hash = self._hash_string(url)
            return f"{company_clean}_{source_clean}_{url_hash}"

        return f"{company_clean}_{source_clean}"

    # ========================================================================
    # LLM CACHE
    # ========================================================================

    def get_llm_response(self, prompt: str, model: str) -> Optional[dict[str, Any]]:
        """
        Retrieve cached LLM response.

        Args:
            prompt: The prompt sent to the LLM
            model: Model name (e.g., 'llama-3.3-70b-versatile')

        Returns:
            Cached LLM response if found and not expired, else None
        """
        if self.debug_mode:
            print("⚠️ Debug mode: LLM Cache skipped")
            return None

        cache_key = self._make_llm_key(prompt, model)
        cache_file = self.llm_dir / f"{cache_key}.json"

        if not cache_file.exists():
            self.stats["llm_misses"] += 1
            self._save_stats()
            return None

        try:
            with open(cache_file, "r") as f:
                cache_data = json.load(f)

            if self._is_expired(cache_data):
                cache_file.unlink()
                self.stats["llm_misses"] += 1
                self._save_stats()
                return None

            # Cache hit - BIG savings!
            self.stats["llm_hits"] += 1
            self.stats["total_api_calls_saved"] += 1
            self.stats["estimated_credits_saved"] += 0.01  # Rough estimate
            self._save_stats()

            return cache_data.get("response")

        except Exception as e:
            print(f"Cache read error: {e}")
            return None

    def set_llm_response(
        self, prompt: str, model: str, response: dict[str, Any]
    ) -> None:
        """
        Store LLM response in cache.

        Args:
            prompt: The prompt sent to the LLM
            model: Model name
            response: LLM response to cache
        """
        cache_key = self._make_llm_key(prompt, model)
        cache_file = self.llm_dir / f"{cache_key}.json"

        cache_entry = {
            "model": model,
            "prompt_hash": self._hash_string(prompt),
            "cached_at": datetime.now().isoformat(),
            "response": response,
        }

        try:
            with open(cache_file, "w") as f:
                json.dump(cache_entry, f, indent=2)
        except Exception as e:
            print(f"Cache write error: {e}")

    def _make_llm_key(self, prompt: str, model: str) -> str:
        """Generate cache key for LLM responses."""
        prompt_hash = self._hash_string(prompt)
        model_clean = model.replace("/", "_").replace(":", "_")
        return f"{prompt_hash}_{model_clean}"

    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = self.stats.copy()

        # Calculate hit rates
        total_scraping = stats["scraping_hits"] + stats["scraping_misses"]
        total_llm = stats["llm_hits"] + stats["llm_misses"]

        if total_scraping > 0:
            stats["scraping_hit_rate"] = (
                f"{(stats['scraping_hits'] / total_scraping * 100):.1f}%"
            )
        else:
            stats["scraping_hit_rate"] = "N/A"

        if total_llm > 0:
            stats["llm_hit_rate"] = f"{(stats['llm_hits'] / total_llm * 100):.1f}%"
        else:
            stats["llm_hit_rate"] = "N/A"

        # Add cache sizes
        stats["scraping_cache_files"] = len(list(self.scraping_dir.glob("*.json")))
        stats["llm_cache_files"] = len(list(self.llm_dir.glob("*.json")))

        return stats

    def clear_cache(self, cache_type: Optional[str] = None) -> dict[str, int]:
        """
        Clear cache entries.

        Args:
            cache_type: 'scraping', 'llm', or None (clears all)

        Returns:
            Count of deleted files
        """
        deleted = {"scraping": 0, "llm": 0}

        if cache_type in (None, "scraping"):
            for file in self.scraping_dir.glob("*.json"):
                file.unlink()
                deleted["scraping"] += 1

        if cache_type in (None, "llm"):
            for file in self.llm_dir.glob("*.json"):
                file.unlink()
                deleted["llm"] += 1

        return deleted

    def clear_expired(self) -> dict[str, int]:
        """
        Remove expired cache entries.

        Returns:
            Count of deleted files by type
        """
        deleted = {"scraping": 0, "llm": 0}

        # Check scraping cache
        for file in self.scraping_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    cache_data = json.load(f)

                if self._is_expired(cache_data):
                    file.unlink()
                    deleted["scraping"] += 1
            except Exception:
                pass

        # Check LLM cache
        for file in self.llm_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    cache_data = json.load(f)

                if self._is_expired(cache_data):
                    file.unlink()
                    deleted["llm"] += 1
            except Exception:
                pass

        return deleted


# Global cache instance
_cache: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get global cache manager instance."""
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache
