# 🏛️ Peters Luxury Realty — AI Concierge "Riley"

> A 24/7 AI lead-capture concierge for a fictional Beverly Hills luxury real estate firm. Built from scratch in a weekend.

**🌐 [Live demo →](https://peters-luxury-realty.onrender.com)**

![Riley in action](screenshots/chat-interface.png)

---

## What this is

Riley is an AI agent powered by Anthropic's Claude that has natural conversations with luxury real estate buyers. She answers questions about a curated portfolio of 24 LA listings ($2.95M–$45M), qualifies serious buyers using Fair Housing-compliant questions, and captures leads in real-time across three channels: a CSV log, an email notification to the firm, and a live-syncing Google Sheet.

The point of the project: real estate firms have basic chat widgets. Riley is what those widgets *should* be — actually intelligent, on-brand, and useful from minute one.

## Demo

- **Live site:** https://peters-luxury-realty.onrender.com
- **Try this:** "I'm interested in a Malibu beachfront. My name is Erik and you can reach me at 555-555-5555." Riley will qualify you, save the lead, and (if I haven't disabled it) email me about you.

## Screenshots

| Chat interface | Lead notification email | Google Sheets sync |
|---|---|---|
| ![Chat](screenshots/chat.png) | ![Email](screenshots/email.png) | ![Sheets](screenshots/sheet.png) |

## Architecture
Browser ──→ Flask server ──→ Claude API (Sonnet 4.5)
│
↓
Lead capture pipeline:
├─→ leads.csv (local log)
├─→ Resend (luxury-branded email notification)
└─→ Google Sheets API (live sync)
The clever bit: Riley uses **two Claude calls per response** — one for the conversation itself, one for structured JSON extraction to detect when the user has shared enough info to be considered a qualified lead. The lead extractor returns `{lead: true/false, name, contact, interest}` which the server uses to decide whether to fire the notification pipeline.

## Tech stack

- **Backend:** Python, Flask, gunicorn
- **AI:** Anthropic Claude Sonnet 4.5
- **Email:** Resend (with custom HTML templates)
- **Data sync:** Google Sheets API via `gspread` + service account auth
- **Frontend:** Vanilla HTML / CSS / JavaScript (Playfair Display + Inter typography)
- **Hosting:** Render (auto-deploys from GitHub on every push)
- **Source control:** Git + GitHub

## What this project demonstrates

- Designing and shipping a complete full-stack AI application end-to-end
- LLM prompt engineering for a custom-personality, on-brand agent with hard constraints (Fair Housing compliance, never invent listings, etc.)
- Multi-step LLM workflows (chat response + parallel structured lead extraction)
- Google Cloud service account auth — the same pattern used for Calendar, Gmail, and most enterprise integrations
- Production secrets management (env vars, gitignored credentials, env-var fallback for the credentials JSON in production)
- Visual design for a specific brand aesthetic (luxury hospitality — Playfair Display serif, espresso #2a2520, gold #d4af6c)
- Production CI/CD with auto-deploy on `git push`
- HTTP API design with Flask + CORS

## Run it locally

```bash
git clone https://github.com/erikpeters1016-hue/Peters-Luxury-Realty.git
cd Peters-Luxury-Realty
pip install -r requirements.txt
```

Add a `.env` file in the project root:
ANTHROPIC_API_KEY=sk-ant-your-key-here
RESEND_API_KEY=re_your-key-here
LEAD_NOTIFICATION_EMAIL=you@example.com
GOOGLE_SHEET_ID=your-sheet-id-here
Plus a `google-credentials.json` file from a Google Cloud service account with Sheets + Drive API access (the sheet must be shared with the service account's email as Editor).

Then:

```bash
python3 server.py
```

Visit `http://localhost:8000`

## What I learned

This was my first real software project. I started Day 1 with zero coding experience and ended with a deployed, multi-service AI application running on the public internet. The most valuable lessons weren't technical — they were:

- **Reading error messages is a skill.** Every bug I hit was solvable; the job was learning to actually read what Python was telling me instead of panicking.
- **Secrets management is non-negotiable.** I exposed an API key once during debugging. GitHub Push Protection caught it, I rotated the key, and I learned to take env vars seriously.
- **`grep` is your best friend.** When the deployed code seems out of sync with what you're seeing in your editor, a 5-second `grep` check is worth more than 30 minutes of guessing.
- **Shipping > polishing.** The first Render deploy was scary. By the fifth, it was routine. The fastest way to get over the fear of deployment is to deploy a lot.
- **Indentation matters in Python.** A misplaced 4 spaces nested an entire function inside another function's `except` block, which caused the most confusing bug of the project.

## What's next

This project is a portfolio piece, not a real business. The full lead pipeline works, but I'm not pursuing real estate AI as a startup — every firm already has a chatbot, and it's a crowded category.

The skills I built here are now feeding a different idea: an HIPAA-compliant AI scribe for telehealth therapists, who currently spend 30-60 minutes after every session writing reports in company-specific templates. That's the real problem worth solving.

---

**Built by Erik Peters** · [erikpeters1016@gmail.com](mailto:erikpeters1016@gmail.com)