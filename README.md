# CareerOS

**CareerOS** is a professional, AI-powered career intelligence platform designed to autonomously discover, filter, rank, and explain job and internship opportunities for candidates.

## Core Features

- **Multi-Source Job Discovery**: Seamlessly fetches jobs from multiple platforms including JSearch, Adzuna, Remotive, RemoteOK, and Arbeitnow.
- **Intelligent Filtering & Deduplication**: Normalizes job data, eliminates duplicates using URL and content hashing, and enforces hard deterministic filters (e.g., location, employment type).
- **Evidence-Based Matching**: Leverages vector search (Qdrant) alongside LLMs (Google Gemini, local Llama models) to evaluate candidate fit and provide explainable evidence for recommended matches.
- **Verification Engine**: Validates job posting integrity to ensure listings are still active and accepting applications.
- **High-Performance Stack**: Built from the ground up using FastAPI, LangGraph, SQLAlchemy, and Granian for low-latency asynchronous processing.

---

## Required APIs and Services

CareerOS integrates with several external APIs for discovery and intelligence. While the platform gracefully degrades and functions with zero API keys (using free job sources), adding keys unlocks its full potential.

| Service | Purpose | Cost / Free Tier | How to Obtain API Key |
|---|---|---|---|
| **Remotive** | Remote-only tech jobs | **Free** (No key needed) | *Pre-configured automatically.* |
| **RemoteOK** | Remote, startup jobs | **Free** (No key needed) | *Pre-configured automatically.* |
| **Arbeitnow** | EU & India remote jobs | **Free** (No key needed) | *Pre-configured automatically.* |
| **JSearch** | Global job aggregation | ~200 requests/month free | Sign up at [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QG1q/api/jsearch) and subscribe to the basic tier. |
| **Adzuna** | Global jobs | ~1,000 requests/month free | Register at [Adzuna Developer](https://developer.adzuna.com/) and create an app to get your `APP_ID` and `APP_KEY`. |
| **Firecrawl** | Job live verification | 500 credits/month free | Sign up at [Firecrawl.dev](https://www.firecrawl.dev/) and generate an API key. |
| **Google Gemini** | LLM for matching | Generous free tier | Generate an API key at [Google AI Studio](https://aistudio.google.com/app/apikey). |

---

## Installation and Setup

### Prerequisites

- **Python 3.12+**
- **Git**
- **MySQL** (Optional: If omitted, the system defaults to local SQLite for development)

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
.venv\Scriptsctivate
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
*Note: If you leave `DATABASE_URL` blank, CareerOS will automatically default to a local SQLite database for ease of setup.*

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

---

## Testing

To run the automated test suite and ensure all components are functioning correctly:

```bash
pytest -v
```

## Production Deployment

For production environments, ensure you have configured a production-ready MySQL instance in your `.env` via `DATABASE_URL` and set `APP_ENV=production`. Start the server utilizing multiple workers for high concurrency:

```bash
python run.py --host 0.0.0.0 --port 8000 --workers 4
```
