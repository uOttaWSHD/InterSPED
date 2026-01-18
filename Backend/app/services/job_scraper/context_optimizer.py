import json
from typing import Any, List, Dict


def optimize_context(raw_data: List[Dict[str, Any]], max_chars: int = 8000) -> str:
    """
    Trims and cleans raw scraped data to reduce token usage.
    Removes repetitive fields and unnecessary metadata.
    """
    optimized_parts = []

    for item in raw_data:
        source = item.get("source_name", "Unknown")
        data = item.get("data", {})

        if source == "LeetCode Problems":
            # Only include first 10 problem titles/summaries to save tokens
            problems = data.get("problems", [])
            summarized_problems = []
            for p in problems[:10]:
                summarized_problems.append(
                    {
                        "id": p.get("leetcode_number"),
                        "title": p.get("title"),
                        "diff": p.get("difficulty"),
                        # Truncate statement if it's too long
                        "stmt": (p.get("problem_statement") or "")[:200] + "...",
                    }
                )
            optimized_parts.append(
                f"=== {source} ===\n{json.dumps(summarized_problems)}"
            )

        elif source == "Job Posting":
            # Extract key text, avoid long legal footers
            full_text = str(data.get("full_content", ""))
            # Usually the first 4000 chars have the meat
            optimized_parts.append(f"=== {source} ===\n{full_text[:4000]}")

        elif source == "Glassdoor Interviews":
            # Only take the first 5 reviews
            interviews = data.get("interviews", [])[:5]
            optimized_parts.append(f"=== {source} ===\n{json.dumps(interviews)}")

        else:
            optimized_parts.append(f"=== {source} ===\n{json.dumps(data)}")

    combined = "\n\n".join(optimized_parts)
    return combined[:max_chars]
