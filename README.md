 chmod +x start.sh && ./start.sh  
# Ask What Matters — HB Presents

Wharton Hack-AI-thon 2026 submission for the **"Adaptive AI for Smarter Travel Reviews"** challenge.

## What this is

A deterministic agent that decides up to **3 targeted follow-up questions** to ask a guest after they submit a hotel review. The questions are ranked by an empirical "gap priority" score derived from analyzing 5,999 reviews across 7 languages (English, Spanish, German, French, Italian, Portuguese, Japanese + Chinese).

Design philosophy:
- **Rules pick the questions. LLMs only polish the wording.** This keeps behavior testable and removes a class of hallucination / prompt-injection bugs.
- Priorities come from real data, not intuition. Bathroom issues score 8.84; billing scores 5.08; location scores 1.80. The agent asks what matters most first.

## 🚀 Quick Start (Local Docker)

The easiest way to run the full stack (Frontend + Backend) is by using the provided automation script.

### 1. Configure API Key

Edit `backend/.env` and add your OpenAI API key:

```bash
OPENAI_API_KEY=your_api_key_here
```

### 2. Set Permissions(chmod) & Run

Make the script executable and start the application:

```bash
chmod +x start.sh && ./start.sh
```

### 3. Access the Application

* **Frontend:** http://localhost:5173
* **Backend API:** http://localhost:8000


## Repo layout

```
backend/
  schema.py         # shared dataclasses + enums (ReviewContext, Question, AgentDecision)
  rules.py          # regex aspect detection + light sentiment
  question_bank.py  # 16 candidate questions, each with a trigger condition
  agent.py          # decide_questions(ctx) — the main entry point
  demo.py           # 3 runnable review scenarios
```

## OpenAI setup

Create `backend/.env` with your API key:

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

For Vercel deployment, set the same env vars in the project settings instead of committing them to the repo.

## Run the demo

```bash
cd backend
python demo.py
```

Expected output: three review scenarios (angry short review, happy long review, mixed family review) and the 3 follow-up questions the agent picks for each, plus the rationale.

## Design doc

Full architecture, decision tree, pseudocode, JSON API contracts, and question catalog are in `Backend_Design.docx` (delivered separately to the team).

## Team

HB Presents  ·  Wharton Hack-AI-thon 2026
