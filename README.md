# CareerOS

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

**CareerOS** is a professional, AI-powered career intelligence platform designed to autonomously discover, filter, rank, and explain job and internship opportunities for candidates.

## Table of Contents
- [Overview](#overview)
- [Core Features](#core-features)
- [Architecture](#architecture)
- [Required APIs and Services](#required-apis-and-services)
- [Installation and Setup](#installation-and-setup)
- [Usage](#usage)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

CareerOS automates the job search process by intelligently aggregating listings from multiple sources, applying deterministic filters, performing semantic matching, and providing explainable AI-driven recommendations. The platform is specifically optimized for the Indian job market while maintaining global compatibility.

## Core Features

- **Multi-Source Job Discovery**: Seamlessly fetches jobs from multiple platforms including JSearch, Adzuna, Remotive, RemoteOK, and Arbeitnow.
- **Intelligent Filtering & Deduplication**: Normalizes job data, eliminates duplicates using URL and content hashing, and enforces hard deterministic filters (e.g., location, employment type, experience level, salary, recency).
- **Evidence-Based Matching**: Leverages vector search (Qdrant) alongside LLMs (Google Gemini, local Llama models, OpenRouter, NVIDIA NIM) to evaluate candidate fit and provide explainable evidence for recommended matches.
- **Verification Engine**: Validates job posting integrity to ensure listings are still active and accepting applications.
- **High-Performance Stack**: Built from the ground up using FastAPI, LangGraph, SQLAlchemy, and Granian for low-latency asynchronous processing.
- **India-First Defaults**: Pre-configured for Indian job market (Adzuna India, Hyderabad as default location).

## Architecture

CareerOS follows a modular, service-oriented architecture:

1. **API Layer** (`app/main.py`): FastAPI endpoints for search and matching operations
2. **Workflow Orchestration** (`app/graph.py`): LangGraph state machine managing the job discovery pipeline
3. **Service Layer**: 
   - Job discovery adapters (`app/services/job_api_adapter.py`)
   - Normalization and deduplication (`app/services/normalize.py`, `app/services/dedup.py`)
   - Filtering (`app/services/filters.py`)
   - Vector storage and search (`app/services/vector_store.py`)
   - Embedding generation (`app/services/embeddings.py`)
   - Model routing (`app/services/model_router.py`)
   - Reranking (`app/services/reranker.py`)
   - Verification (`app/services/verification.py`)
4. **Data Layer**: SQLAlchemy ORM with MySQL backend (`app/models.py`)
5. **User Interface**: Gradio-based web dashboard (`app/gradio_app.py`)

The system implements hard eligibility filters at the database level (spec 2.1) ensuring LLMs never override core constraints.

## Required APIs and Services

CareerOS integrates with several external APIs for discovery and intelligence. While the platform gracefully degrades and functions with zero API keys (using free job sources), adding keys unlocks its full potential.

| Service | Purpose | Cost / Free Tier | How to Obtain API Key |
|---|---|---|---|
| **Remotive** | Remote-only tech jobs | **Free** (No key needed) | *Pre-configured automatically.* |
| **RemoteOK** | Remote, startup jobs | **Free** (No key needed) | *Pre-configured automatically.* |
| **Arbeitnow** | EU & India remote jobs | **Free** (No key needed) | *Pre-configured automatically.* |
| **JSearch** | Global job aggregation | ~200 requests/month free | Sign up at [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QG1q/api/jsearch) and subscribe to the basic tier. |
| **Adzuna** | Global jobs (default: India) | ~1,000 requests/month free | Register at [Adzuna Developer](https://developer.adzuna.com/) and create an app to get your `APP_ID` and `APP_KEY`. |
| **Firecrawl** | Job live verification | 500 credits/month free | Sign up at [Firecrawl.dev](https://www.firecrawl.dev/) and generate an API key. |
| **Google Gemini** | LLM for matching | Generous free tier | Generate an API key at [Google AI Studio](https://aistudio.google.com/app/apikey). |
| **llama.cpp** | Local LLM (optional) | Free, runs locally | Install [llama.cpp](https://github.com/ggerganov/llama.cpp) and run a model server. |
| **OpenRouter** | 100+ models (Claude, GPT, Llama) | Free tier: `meta-llama/llama-3.1-8b-instruct:free`, `google/gemma-2-9b-it:free`, `mistralai/mistral-7b-instruct:free`, `microsoft/phi-3-mini-128k-instruct:free` | Get key at [OpenRouter](https://openrouter.ai/keys) |
| **NVIDIA NIM** | Optimized inference microservices | Free tier: `meta/llama-3.1-8b-instruct`, `google/gemma-2-9b-it` | Get key at [NVIDIA Build](https://build.nvidia.com/explore/discover) |

---

## Installation and Setup

### Prerequisites

- **Python 3.12+**
- **Git**
- **MySQL** (Required: the system uses MySQL for development and production)

### 1. Clone the Repository

```bash
git clone https://github.com/VaddiMaithresh-16/CareerOS.git
cd CareerOs
```

### 2. Set Up Virtual Environment

#### macOS and Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows (Command Prompt / PowerShell)
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create your environment configuration by copying the template file:

#### macOS and Linux
```bash
cp .env.example .env
```

#### Windows
```cmd
copy .env.example .env
```

Open `.env` in your preferred text editor and add your acquired API keys.

**Database Configuration (MySQL Required):**
CareerOS requires MySQL. Use `MYSQL_*` components to auto-construct the database URL. Set these in `.env`:
```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=careeros
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
```

The app automatically builds: `mysql+pymysql://USER:PASSWORD@HOST:PORT/DATABASE`

**Alternative:** Set explicit `DATABASE_URL` (overrides MYSQL_* above):
```bash
# MySQL local
DATABASE_URL=mysql+pymysql://user:pass@127.0.0.1:3306/careeros
# MySQL Docker
DATABASE_URL=mysql+pymysql://user:pass@mysql:3306/careeros
```

**Key defaults for India:**
- `ADZUNA_COUNTRY=in` (Adzuna India)
- Default location in UI: "Hyderabad, India"

---

## Usage

Start the backend API and the user interface.

### 1. Start the API Server (Granian)

Run the following command in your terminal. This will spin up the FastAPI backend on port `8000`.

```bash
python run.py
```

### 2. Start the User Interface (Gradio)

Open a **new terminal window**, activate your virtual environment, and run:

```bash
python app/gradio_app.py
```

### 3. Access the Application

- **Web Interface:** Open your browser and navigate to `http://127.0.0.1:7860` to access the CareerOS dashboard.
- **API Documentation:** Navigate to `http://127.0.0.1:8000/docs` to view the interactive Swagger API documentation.

### 4. Gradio UI Features

The web interface supports advanced search filters:
- **Role/Query**: Job title or keywords (required)
- **Location**: City, state, or region (default: Hyderabad, India)
- **Remote Only**: Filter for fully remote positions
- **Employment Type**: Full-time, Part-time, Internship, Contract, Temporary
- **Experience Level**: Intern, Fresher, Entry, Mid, Senior
- **Minimum Salary**: Annual salary floor (in local currency)
- **Posted Within**: Recency filter in days
- **LLM Provider**: auto / llama / gemini / openrouter / nvidia / none
- **Model**: Model selection dropdown (populated based on provider)

### 5. Auto Mode Fallback Chain (LLM_PROVIDER_MODE=auto)

When set to `auto`, the system tries providers in this order until one succeeds with confidence ≥ 0.6:
1. **Local llama.cpp** — Private, fast, free (requires local server)
2. **NVIDIA NIM** — Optimized inference, free tier available
3. **OpenRouter** — 100+ models, free tier available
4. **Google Gemini** — Generous free tier

---

## Testing

To run the automated test suite and ensure all components are functioning correctly:

```bash
pytest -v
```

The test suite covers:
- Job discovery adapters
- Normalization and deduplication
- Hard filter application
- Vector store operations
- Model routing logic
- Middleware functionality
- End-to-end workflows

All 52 tests should pass.

---

## Production Deployment

For production environments, ensure you have configured a production-ready MySQL instance in your `.env` via `MYSQL_*` components (or explicit `DATABASE_URL`) and set `APP_ENV=production`. Start the server utilizing multiple workers for high concurrency:

```bash
python run.py --host 0.0.0.0 --port 8000 --workers 4
```

**Production Checklist:**
- Set `API_KEY` in `.env` to enable authentication
- Configure `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` for production MySQL
- Configure `QDRANT_URL` for a hosted Qdrant instance
- Use Redis-backed rate limiter (replace in-memory limiter)
- Set up proper logging/monitoring
- Configure `FIRECRAWL_API_KEY` for job verification
- Use a real embedding model (replace HashingVectorizer) for production semantic search
- Set `APP_ENV=production` (enables MySQL, disables SQLite fallback)

---

## Contributing

We welcome contributions to CareerOS! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows:
- PEP 8 style guidelines
- Includes appropriate tests
- Passes all existing tests
- Documents new functionality

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), and [Gradio](https://www.gradio.app/)
- Job data sourced from JSearch, Adzuna, Remotive, RemoteOK, and Arbeitnow APIs
- LLM capabilities powered by Google Gemini, NVIDIA NIM, OpenRouter, and local llama.cpp models