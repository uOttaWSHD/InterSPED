# Intersped

[Intersped](https://intersped-jmlsj.ondigitalocean.app/) is a real-time, AI-powered technical interview simulator designed to give job seekers a personalized and immersive preparation experience. By scraping company-specific data—including mission, culture, technical stacks, and even company-relevant LeetCode problems—Intersped tailors every interview to the specific role and company you're targeting.

## 🚀 Key Features

- **Company-Specific Scraping**: Automatically gathers insights on company mission, culture, and interview processes using the agentic **JobScraper** powered by Yellowcake.
- **Real-Time Voice Interaction**: Seamless, low-latency voice interviews using **ElevenLabs** for industry-leading Speech-to-Text (STT) and Text-to-Speech (TTS).
- **Dynamic AI Personas**: Powered by **Solace Agent Mesh (SAM)**, the AI interviewer ("John") adapts its personality and technical focus based on the scraped company data.
- **Barge-In Support**: Natural conversation flow where users can interrupt the AI, just like in a real interview.
- **Technical & Behavioral Depth**: Covers everything from system design and coding challenges to cultural fit and behavioral questions.
- **Integrated Environment**: Built-in code editor and dashboard to track your progress and interview history.

## 🛠️ Tech Stack

### Frontend
- **Framework**: [Next.js 15](https://nextjs.org/) (App Router)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/), [Framer Motion](https://www.framer.com/motion/)
- **UI Components**: [Radix UI](https://www.radix-ui.com/), [Lucide React](https://lucide.dev/)
- **Authentication**: [Better-Auth](https://www.better-auth.com/)
- **State Management**: React Hooks & Context API

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Orchestration**: [Solace Agent Mesh (SAM)](https://solace.com/)
- **AI/LLM**: [LangChain](https://www.langchain.com/), [Groq](https://groq.com/), [DSPy](https://github.com/stanfordnlp/dspy)
- **Voice/Audio**: [ElevenLabs](https://elevenlabs.io/) (STT, TTS, VAD)
- **Scraping Engine**: Yellowcake, Playwright, BeautifulSoup4
- **Database**: Better-SQLite3 (via Better-Auth)

## 📁 Project Structure

```
.
├── Backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/          # Pydantic data models
│   │   ├── routers/         # API endpoints (voice, scraper, interview)
│   │   ├── services/        # Business logic (SAM, voice, scraper)
│   │   │   └── job_scraper/ # Advanced agentic scraping engine
│   │   └── utils/           # Helper functions
│   ├── pyproject.toml       # Python dependencies
│   └── Dockerfile
├── Frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/             # Next.js pages & layouts
│   │   ├── components/      # UI components (interview room, dashboard)
│   │   ├── hooks/           # Custom React hooks (voice logic)
│   │   └── lib/             # Utilities and auth config
│   ├── package.json         # Node.js dependencies
│   └── Dockerfile
├── app.yaml                 # Deployment configuration
└── intersped.db             # Local SQLite database
```

## ⚙️ Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (recommended for Python package management)

### Environment Variables

Create a `.env` file in the root directory with the following:

```env
# Backend
YELLOWCAKE_API_KEY=your_key
GROQ_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
LLM_SERVICE_API_KEY=your_key
LLM_SERVICE_ENDPOINT=your_endpoint

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
BETTER_AUTH_SECRET=your_secret
DISCORD_CLIENT_ID=your_id
DISCORD_CLIENT_SECRET=your_secret
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Installation & Setup

#### The Quick Way (Recommended)
You can start both the frontend and backend with a single command using the provided setup script:

```bash
chmod +x start.sh
./start.sh
```
This script will sync dependencies, migrate the database, and launch both services (Frontend on 3000, Backend on 8000/8001).

#### Manual Setup

##### 1. Backend
```bash
cd Backend
uv sync
uv run python run_all.py
```

##### 2. Frontend
```bash
cd Frontend
npm install
npm run dev
```

The application will be available at `http://localhost:3000`.

## 🧠 How it Works

1. **Scraping Phase**: When you start an interview, the **JobScraper** uses multi-source agents to research the company and the specific role.
2. **Context Injection**: This data is fed into the **Solace Agent Mesh**, which configures a specialized technical interviewer persona.
3. **Voice Loop**: The frontend opens a WebSocket connection to the backend. Audio is captured from your mic, transcribed via ElevenLabs, processed by the AI persona, and synthesized back into speech.
4. **Analysis**: After the session, the platform analyzes your performance based on the specific requirements of the company you "interviewed" for.

## 🛡️ Resiliency: Key Rotation System

To ensure uninterrupted service during high traffic or hackathon usage, Intersped implements a **comma-separated key rotation system**.
- **Automatic Failover**: The backend automatically cycles through multiple API keys for ElevenLabs, Groq, and Yellowcake.
- **Rate-Limit Handling**: If one key hits a rate limit or fails, the system seamlessly moves to the next available key without interrupting the user's interview.

## 🚢 Deployment

The project is optimized for deployment on **DigitalOcean App Platform** using the provided `app.yaml`.

### Steps:
1. Push the repository to GitHub.
2. Create a new App on DigitalOcean.
3. Link the repository and the App Platform will automatically detect the components via `app.yaml`.
4. Define your environment variables in the DigitalOcean Control Panel (use comma-separated strings for keys you want to rotate).

## 📄 License

This project was built for uOttahack 2026.
