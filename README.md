# Pocket Therapist 🌙

A quiet 5-minute conversation app for men's mental health. Built to feel like texting a friend who happens to understand psychology — not a clinical bot.

## What it is

- **One core loop**: open the app → tap Talk → have a real 5-minute conversation → close the app feeling slightly more sorted
- **Three screens only**: Home, Conversation, Past Sessions
- **Local & private**: your sessions stay on your machine (SQLite)
- **Streaming responses**: feels alive, not robotic

## Stack

- **Streamlit** — chat UI
- **Groq + Llama 3.3 70B** — fast, conversational LLM
- **SQLite (WAL mode)** — local session storage
- **python-dotenv** — config

## Setup

1. **Clone & enter the project**
   ```bash
   cd pocket-therapist
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv .venv
   source .venv/bin/activate     # macOS/Linux
   .venv\Scripts\activate        # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your Groq API key**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and paste your key from [console.groq.com](https://console.groq.com).

5. **Run**
   ```bash
   streamlit run app.py
   ```

   Open the URL Streamlit prints (usually `http://localhost:8501`).

## Project Structure

```
pocket-therapist/
├── app.py                  # Streamlit entry point + UI
├── core/
│   ├── prompts.py          # The personality (the soul of the product)
│   ├── conversation.py     # Groq client + streaming logic
│   └── storage.py          # SQLite sessions & messages
├── utils/
│   └── logger.py           # Centralized logger
├── data/                   # SQLite DB lives here (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Key Design Decisions

See `DECISIONS.md` for the full reasoning. Highlights:

- **The system prompt is the product.** Tone, length, what it never says — all baked into one file.
- **Streaming over blocking** — a 4-second pause kills the conversational feel.
- **Wrap-up nudge after 6 user turns** — prevents the infinite-chat trap.
- **No graphs, no scores** — this isn't a tracker, it's a conversation.
- **India-default crisis lines** — locally useful from day one.

## Not a substitute for therapy

This app is for daily check-ins and self-reflection. If you're in crisis, please reach out:
- **India**: iCall — 9152987821 · Vandrevala Foundation — 1860-2662-345
- **Elsewhere**: contact your local crisis line.
# AI_mental_companion
