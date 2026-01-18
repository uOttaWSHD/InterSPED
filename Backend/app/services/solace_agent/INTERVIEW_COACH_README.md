# AI Interview Coach - Simplified

A simple 3-agent interview coaching system using Solace Agent Mesh.

## Agents

### 1. **Orchestrator Agent**
Routes requests to the right coach:
- **"answer"** or **"analyze"** → DeliveryAgent
- **"summary"** or **"interview ended"** → SummaryAgent

### 2. **DeliveryAgent** 
Your real-time interview coach during the interview.
- Give your answer to any interview question
- Get instant, encouraging feedback
- Get tips on how to improve the answer
- Have a natural conversation - ask follow-ups!

**Use when**: You want feedback on a specific interview answer

### 3. **SummaryAgent**
Gives you a complete summary when your interview is done.
- Tells you what you did well (with specifics)
- Shows you the main areas to improve
- Gives you a concrete action plan
- Rates your overall performance

**Use when**: Your interview session is complete

## How to Use

1. **Start the system (fastest):**
   ```bash
   ./start.sh
   ```

2. **Or start manually:**
   ```bash
   uv sync
   uv run sam run configs/
   ```

3. **Open the web UI:** http://localhost:8000

4. **During Interview:**
   - Say: "I was asked 'Tell me about a challenge you faced' and I answered..."
   - DeliveryAgent gives you feedback instantly
   - Ask follow-up questions if you want more help

4. **After Interview:**
   - Say: "My interview is done, give me a summary"
   - SummaryAgent summarizes everything and gives you next steps

## Examples

### Getting Feedback
```
User: "Question: 'What's your biggest weakness?' 
       My answer: 'I tend to be a perfectionist, so I...'"

DeliveryAgent: "That's a great weakness to mention! I like how you showed 
self-awareness. Next time, make sure you show how you FIXED it. 
Try saying: 'I realized this and started doing X to improve.'"
```

### Getting a Summary
```
User: "My interview just ended. I answered 5 questions. 
       Give me a summary and action plan."

SummaryAgent: "Great job! Here's what I saw...
What You Did Well:
- Strong STAR method on the challenge question
- Good examples with specifics

Areas to Improve:
- Practice more on technical questions
- Show more enthusiasm about the company

Action Plan:
1. Do 5 more technical practice questions
2. Research the company more deeply
3. Practice out loud 3x before your next interview

Overall: You scored 7/10 - you're ready, just needs polish!"
```

## System Setup

`.env` required:
```
LLM_SERVICE_ENDPOINT=https://generativelanguage.googleapis.com/v1beta
LLM_SERVICE_API_KEY=your-api-key
LLM_SERVICE_PLANNING_MODEL_NAME=gemini/gemini-2.0-flash-lite
LLM_SERVICE_GENERAL_MODEL_NAME=gemini/gemini-2.0-flash-lite
SOLACE_DEV_MODE=true
```

(See `.env.example` for free API options like Cerebras)

## Files

- `start.sh` - Easy startup script
- `configs/agents/orchestrator.yaml`
- `configs/agents/delivery-agent.yaml`
- `configs/agents/summary-agent.yaml`

All agents share config from `configs/shared_config.yaml`

---

**That's it! Simple, focused, effective interview coaching.** ✨
