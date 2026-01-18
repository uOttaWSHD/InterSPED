# JobScraper Architecture

## Overview
JobScraper uses a **multi-stage intelligent pipeline** to transform company names into comprehensive interview preparation materials.

## Why This Architecture?

**The Problem**: You can't just scrape and magically get structured interview insights. Raw scraped data is messy, unstructured, and needs intelligent analysis.

**The Solution**: Multi-stage pipeline combining web scraping (Yellowcake) with LLM analysis (OpenAI).

## Pipeline Stages

### Stage 1: RAW DATA SCRAPING (Yellowcake & Custom) 🔍
**Purpose**: Get unfiltered interview experiences and company data from the web

**What it does**:
- **Yellowcake**: Intelligently scrapes LeetCode problem details (structure extraction)
- **Custom Scrapers**:
  - Fetches company problem lists from GitHub (CSV)
  - Scrapes Glassdoor interview experiences
  - Grabs company career pages and mission statements
- Extracts job postings if provided

**Yellowcake's Role**:
- Navigates dynamic LeetCode pages
- Uses agentic prompts to extract structured problem data (description, constraints, examples)
- Handles layout variations automatically
- Provides resilient scraping compared to brittle CSS selectors

**Output**: Raw text and structured JSON about the company and interviews

### Stage 2: INTELLIGENT ANALYSIS (OpenAI LLM) 🤖
**Purpose**: Read through raw data like a human would and extract patterns

**What it does**:
- Analyzes all scraped text
- Identifies common interview questions
- Recognizes patterns in interview processes
- Extracts company culture insights
- Structures technical requirements
- Finds preparation tips

**LLM's Role**:
- Acts as an expert interview coach
- Understands context and nuance
- Structures unstructured data
- Identifies recurring themes
- Generates actionable insights

**Output**: Structured JSON matching our Pydantic models

### Stage 3: VALIDATION & FORMATTING 📦
**Purpose**: Convert LLM output to type-safe Pydantic models

**What it does**:
- Validates LLM output
- Maps to our strict contracts
- Handles edge cases
- Provides fallback if analysis fails

**Output**: `CompanyInterviewDataResponse` - ready to use!

## Data Flow

```
User Input (company name)
        ↓
    [STAGE 1]
 Yellowcake Scraping
        ↓
  Raw text data (JSON)
        ↓
    [STAGE 2]
  OpenAI LLM Analysis
        ↓
 Structured insights (JSON)
        ↓
    [STAGE 3]
 Pydantic Validation
        ↓
CompanyInterviewDataResponse
```

## Why Yellowcake + LLM?

### Yellowcake Strengths:
- ✅ Handles complex web scraping (auth, JS, dynamic content)
- ✅ Navigates multi-page sources
- ✅ Extracts large volumes of text
- ✅ Sponsors the hackathon 🎉

### Yellowcake Limitations:
- ❌ Can't "understand" what it scraped
- ❌ Doesn't extract patterns across multiple sources
- ❌ Can't structure unstructured data intelligently

### LLM Strengths:
- ✅ Understands context and meaning
- ✅ Identifies patterns and themes
- ✅ Structures unstructured information
- ✅ Generates actionable insights

### LLM Limitations:
- ❌ Can't scrape websites
- ❌ No access to fresh data
- ❌ Hallucinates without grounding data

### Combined = Perfect Solution! 🚀
Yellowcake gets the data, LLM makes sense of it.

## Example Flow

### Input:
```json
{
  "company_name": "Google",
  "position": "Software Engineer"
}
```

### Stage 1 Output (Yellowcake):
```
Raw text from Glassdoor:
"I interviewed at Google for SWE. Process was 5 rounds...
First was phone screen with recruiter, then coding challenge...
Asked me to reverse a linked list, implement LRU cache...
Culture is very collaborative, they care about innovation..."

Raw text from careers page:
"At Google, we value creativity and problem-solving...
Our mission is to organize the world's information..."
```

### Stage 2 Output (LLM):
```json
{
  "company_overview": {
    "name": "Google",
    "mission": "Organize the world's information",
    "culture": "Collaborative, innovation-focused"
  },
  "interview_questions": [
    {
      "question": "Reverse a linked list",
      "category": "technical",
      "difficulty": "medium"
    },
    {
      "question": "Implement an LRU cache",
      "category": "technical",
      "difficulty": "hard"
    }
  ],
  "interview_process": {
    "stages": [
      {
        "stage_name": "Phone Screen",
        "duration": "30 minutes",
        "format": "Video call"
      },
      {
        "stage_name": "Coding Challenge",
        "duration": "1 hour",
        "format": "HackerRank"
      }
    ],
    "total_duration": "4-6 weeks"
  }
}
```

### Stage 3 Output (Final):
Validated `CompanyInterviewDataResponse` Pydantic model ready for the API response!

## Benefits

1. **Accuracy**: Real data from Yellowcake, intelligent analysis from LLM
2. **Freshness**: Always scraping latest interview experiences
3. **Structure**: Type-safe Pydantic contracts
4. **Actionable**: Specific questions, tips, and preparation advice
5. **Hackathon-friendly**: Uses Yellowcake (sponsor!) + OpenAI

## Future Enhancements

- Cache frequently requested companies
- Add more sources (LinkedIn, Blind, etc.)
- Multi-LLM validation for higher accuracy
- Personalized interview prep based on user background
- Mock interview generation using the structured data
