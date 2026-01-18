# Yellowcake Integration in JobScraper

We have successfully integrated **Yellowcake** into the `JobScraper` pipeline to enhance data extraction capabilities.

## Where is it used?

Yellowcake is currently used in the **LeetCode Scraper** (`leetcode_scraper.py`) to intelligently extract structured problem details from `leetcode.ca`.

## How it works

1.  **Discovery**: The scraper first identifies the URL for a specific LeetCode problem (e.g., `https://leetcode.ca/2024-01-15-3000-Problem-Title/`).
2.  **Yellowcake Request**: Instead of writing brittle BeautifulSoup parsers for every possible page layout, we send the URL to Yellowcake with a natural language prompt.
3.  **Prompt**:
    ```text
    Extract the following LeetCode problem details:
    - leetcode_number (integer)
    - title (string)
    - difficulty (string)
    - problem_statement (full description text)
    - examples (list of strings)
    - constraints (list of strings)
    - similar_questions (list of strings, optional)
    
    Return structured JSON.
    ```
4.  **Extraction**: Yellowcake uses its agentic capabilities to read the page, understand the content (even if the layout changes), and return the exact JSON structure we requested.
5.  **Fallback**: If the Yellowcake API key is missing or the request fails, the system automatically falls back to the legacy `BeautifulSoup` scraper.

## Benefits

*   **Resilience**: Page layout changes on `leetcode.ca` won't break the scraper.
*   **Accuracy**: Yellowcake is better at distinguishing between the actual problem description and unrelated page content (ads, sidebars).
*   **Simplicity**: We replaced complex parsing logic with a single prompt.

## Configuration

Ensure your `.env` file has the following:

```env
YELLOWCAKE_API_KEY=your_key_here
YELLOWCAKE_API_URL=https://api.yellowcake.dev/v1/extract-stream
```
