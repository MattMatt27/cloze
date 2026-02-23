# Cloze

Cloze is a clinical conversation platform that enables structured, AI-mediated communication between patients and providers. Providers configure time-boxed conversation windows with specific therapeutic prompts, patients engage asynchronously, and the system generates clinical reports when windows close.

Live at [cloze.uk](https://cloze.uk)

## Quick Start

### Prerequisites

- Python 3.9+
- [Homebrew](https://brew.sh) (macOS)

### Installation

```bash
git clone https://github.com/MattMatt27/cloze.git
cd cloze

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Add at least one LLM provider API key to `.env`:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
```

### Run

```bash
python manage.py
```

Open [http://localhost:5051](http://localhost:5051). The first run seeds the database with demo users.

**Demo accounts:**

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Provider | `provider1` | `provider123` |
| Patient | `user1` | `user123` |

### PDF Reports (optional)

```bash
brew install pango
```

This enables PDF export alongside HTML. Without it, PDF downloads fall back to HTML.

### Local LLM with Ollama (optional)

```bash
brew install ollama
ollama serve              # keep running in one terminal
ollama pull llama3.2:1b   # in another terminal
```

Provides on-device AI summaries in reports without cloud API calls.

## Architecture

Flask + SQLAlchemy + Jinja2 templates + Tailwind CSS (CDN). SQLite in development, PostgreSQL-ready for production.

```
cloze/
├── llm_chat/                 # Flask application
│   ├── models/               # SQLAlchemy models
│   │   ├── core.py           #   User, ProviderPatient, Model, SystemPrompt
│   │   ├── chat_window.py    #   ChatWindow, ChatTemplate
│   │   ├── chat.py           #   Conversation, Message, Selection
│   │   ├── report.py         #   Report
│   │   ├── safety_plan.py    #   SafetyPlan
│   │   └── settings.py       #   ProviderSettings
│   ├── routes/               # API + page routes
│   │   ├── auth.py           #   Login/logout
│   │   ├── admin.py          #   Admin dashboard
│   │   ├── provider.py       #   Provider dashboard + patient management
│   │   ├── chat_windows.py   #   Window CRUD, conversation lifecycle
│   │   ├── conversations.py  #   Patient-facing pages
│   │   ├── reports.py        #   Report generation, download, config
│   │   └── safety_plan.py    #   Safety plan CRUD + approval workflow
│   ├── services/
│   │   ├── llm_interface.py  #   Multi-provider LLM client (OpenAI, Anthropic, Google, Ollama)
│   │   ├── report_utils.py   #   Report generation orchestration
│   │   └── report_scheduler.py
│   └── utils/
│       └── decorators.py     #   @role_required
├── prompts/                  # Layered prompt system
│   ├── composer.py           #   compose_system_prompt() — assembles all layers
│   ├── registry.py           #   Domain prompt registry
│   ├── constitutional/       #   Layer 1: identity, safety, scope
│   └── domains/              #   Layer 2: anxiety, depression, trauma, etc.
├── report/                   # Report generation pipeline
│   ├── generator.py          #   UnifiedReportGenerator orchestrator
│   ├── config.py             #   v1/v2 config normalization
│   ├── registry.py           #   Feature registry (available/coming_soon/licensed)
│   ├── base.py               #   ReportComponent base class
│   ├── components/           #   Self-contained analysis components
│   │   ├── ai_summary.py     #     LLM-generated clinical summary
│   │   ├── descriptive_stats.py
│   │   ├── nlp_analysis.py   #     Sentiment, voice, keywords
│   │   ├── cooccurrence_analysis.py
│   │   └── saved_messages.py
│   ├── analyzers/            #   Pure-function analyzers (no DB access)
│   │   ├── sentiment.py
│   │   ├── voice_analysis.py
│   │   ├── keyword_extraction.py
│   │   └── cooccurrence.py
│   ├── renderers/
│   │   ├── html_renderer.py
│   │   └── pdf_renderer.py
│   └── styles/
│       ├── base_styles.py    #   Cloze design tokens
│       ├── academic_styles.py
│       └── pdf_styles.py
├── templates/                # Jinja2 (all extend base.html)
│   ├── base.html             #   Shared layout, sidebar, Tailwind config
│   ├── login.html
│   ├── admin_dashboard.html
│   ├── provider_dashboard.html
│   ├── provider_chat_windows.html
│   ├── user_dashboard.html
│   ├── user_chat_windows.html
│   ├── patient_reports.html
│   └── conversation.html
├── static/
│   ├── js/shared.js          #   Shared utilities (escapeHtml, formatDate, etc.)
│   └── images/logo.png
└── manage.py                 # Entry point + database seeder
```

## Key Concepts

### Chat Windows

A time-boxed period (e.g., one week) during which a patient can have conversations. Providers create windows with one or more **chat templates** — each template has a title, purpose, assigned LLM model, and system prompt. Windows follow a lifecycle: `scheduled` → `active` → `generating_report` → `report_ready`.

### Prompt System

Four-layer prompt composition:
1. **Constitutional** — identity, safety boundaries, scope constraints (markdown files)
2. **Domain** — therapeutic focus area (anxiety, depression, trauma, etc.)
3. **Custom instructions** — provider-written per-template guidance
4. **Safety plan** — patient-specific warning signs, coping strategies, anti-patterns

### Safety Plans

Based on the Stanley-Brown Safety Planning Intervention. Provider creates the clinical framework (anti-patterns, care team, emergency plan), patient fills in their sections (warning signs, coping strategies, support network, reasons for living). Versioned with approval workflow: `draft` → `pending_review` → `active` → `superseded`.

### Reports

Generated when a chat window closes. Both **summary** and **detailed** versions are produced. Components run independently and degrade gracefully if dependencies are unavailable:

- **AI Summary** — LLM-generated clinical narrative (requires Ollama)
- **Descriptive Stats** — message counts, durations, averages
- **NLP Analysis** — sentiment, active/passive voice, emotional keywords
- **Co-occurrence Analysis** — word network graph (matplotlib + networkx)
- **Saved Messages** — patient-flagged quotes from conversations

Download as HTML or PDF in either summary or detailed format.

### Three User Roles

- **Patient** — conversations, safety plan, view own reports
- **Provider** — manage windows/templates, review safety plans, view patient reports
- **Admin** — user management, system overview

## Deployment

The application runs as a Docker container on AWS ECS. See `.aws/` for task definitions and `.github/workflows/` for CI/CD templates.

```bash
docker build -t cloze-app .
docker run -p 5051:5001 --env-file .env cloze-app
```

## License

This work is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Free for academic and research use. Commercial use is not permitted.
