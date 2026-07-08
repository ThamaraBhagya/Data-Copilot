
## 📊 Data Copilot — LLM-Powered Data Analysis Assistant

> Upload any CSV, ask questions in plain English, and get instant charts, statistics, and AI-generated insights — powered by LLaMA 3 via Groq.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.2+-F6C239?logo=chain&logoColor=black)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.24+-013243?logo=numpy&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.7+-11557c)
![Seaborn](https://img.shields.io/badge/Seaborn-0.12+-4C72B0)
![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D?logo=redis&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3.0+-003B57?logo=sqlite&logoColor=white)

---

## 📌 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup (Without Docker)](#local-setup-without-docker)
- [Docker Setup](#docker-setup)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Security](#security)
- [Contributing](#contributing)

---

## Overview

**Data Copilot** is a production-grade, AI-powered data analysis tool that lets anyone — technical or non-technical — analyze CSV datasets through natural language conversation.

Instead of writing pandas or SQL queries, users simply type questions like:

- *"Show me a bar chart of sales by category"*
- *"What are the top 10 customers by total revenue?"*
- *"Is there a correlation between price and quantity?"*

The system uses a **LangChain + Groq (LLaMA 3)** pipeline to generate Python code, executes it inside a **RestrictedPython sandbox** for security, retries automatically on failure, and returns results — charts or tables — directly in the chat UI.

---
## Demo
https://github.com/user-attachments/assets/3a12a083-f722-4da2-8a85-cfe595fba6b9


## Features

| Feature | Description |
|---|---|
| 🧠 **Natural Language Queries** | Ask any data question in plain English |
| 📊 **Automatic Chart Selection** | LLM picks the best chart type before generating code |
| 🔄 **Auto Retry Loop** | Failed code is sent back to the LLM to fix — up to 3 attempts |
| 🔒 **Sandboxed Execution** | All LLM-generated code runs in a RestrictedPython sandbox |
| 💬 **Chat Memory** | Previous questions provide context for follow-up queries |
| 🧾 **Dataset Summary** | AI auto-generates a description, key columns, and suggested questions on load |
| 📁 **Multi-CSV Join** | Load and query across multiple datasets simultaneously |
| ⭐ **Favourites & History** | Save and replay successful queries |
| ⬇️ **Export Results** | Download any table as CSV or chart as PNG |
| 🗄️ **Persistent Storage** | Uploads, history, and favourites survive server restarts |
| ⚡ **Redis Caching** | DataFrames, schemas, and summaries are cached for fast repeat access |
| 📈 **MLflow Tracking** | Every query, generated code, and success/failure is logged |

---
## 🎯 What This Project Demonstrates

| Skill Area | How It's Demonstrated |
| :--- | :--- |
| 🧠 **LLM Engineering** | Prompt engineering, auto-retry loops, and chat memory |
| 🔍 **RAG Concepts** | Schema-aware context injection for accurate code generation |
| 🔒 **Security** | Sandboxed execution using `RestrictedPython` |
| ⚙️ **MLOps** | Experiment and query tracking via MLflow |
| 🌐 **Backend Development**| Modular FastAPI architecture and REST APIs |
| 🖥️ **Frontend / UI** | Interactive, real-time dashboard built with Streamlit |
| 🐳 **DevOps** | Full containerization using Docker & Docker Compose |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User (Browser)                    │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP
┌─────────────────────▼───────────────────────────────┐
│              Streamlit Frontend (8501)               │
│         Upload │ Chat UI │ History │ Favourites      │
└─────────────────────┬───────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────┐
│               FastAPI Backend (8000)                 │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   agent.py  │  │ executor.py  │  │  cache.py  │  │
│  │  LangChain  │  │ Restricted   │  │   Redis    │  │
│  │  Groq LLM   │  │   Python     │  │   Cache    │  │
│  └─────────────┘  └──────────────┘  └────────────┘  │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐                  │
│  │ database.py │  │mlflow_logger │                  │
│  │   SQLite    │  │   MLflow     │                  │
│  └─────────────┘  └──────────────┘                  │
└──────┬──────────────────────────┬───────────────────┘
       │                          │
┌──────▼──────┐          ┌────────▼────────┐
│    Redis     │          │   MLflow (5000) │
│   (6379)     │          │   Experiment    │
│  DataFrame   │          │   Tracking      │
│  Cache       │          └─────────────────┘
└─────────────┘
       │
┌──────▼──────┐
│   SQLite    │
│  copilot.db │
│  History    │
│  Favourites │
│  Metadata   │
└─────────────┘
```

---

## Tech Stack

### Backend
| Tool | Purpose |
|---|---|
| **FastAPI** | REST API framework |
| **LangChain + Groq** | LLM orchestration and inference |
| **LLaMA 3.3 70B** | Primary code generation model |
| **LLaMA 3.1 8B Instant** | Fast chart type selection |
| **RestrictedPython** | Sandboxed execution of LLM-generated code |
| **pandas + matplotlib + seaborn** | Data analysis and visualization |
| **Redis** | DataFrame, schema, and summary caching |
| **SQLite + SQLAlchemy** | Persistent storage for history, favourites, metadata |
| **MLflow** | Experiment and query tracking |

### Frontend
| Tool | Purpose |
|---|---|
| **Streamlit** | Chat UI, file upload, dataset management |

### Infrastructure
| Tool | Purpose |
|---|---|
| **Docker + Docker Compose** | Containerization and orchestration |

---

## Project Structure

```
data-copilot/
├── backend/
│   ├── api/                 # Modular API routes
│   │   ├── copilot.py       
│   │   └── datasets.py      
│   ├── core/                # System configuration
│   │   └── config.py        
│   ├── services/            # Core business logic
│   │   └── dataset.py       
│   ├── main.py              # Lightweight FastAPI entry point
│   ├── agent.py             # LangChain LLM chains and prompt engineering
│   ├── executor.py          # RestrictedPython sandbox (single & multi dataframe)
│   ├── database.py          # SQLAlchemy models and SQLite CRUD operations
│   ├── cache.py             # Redis caching for DataFrames and schemas
│   ├── mlflow_logger.py     # MLflow experiment tracking and telemetry
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py               # Streamlit UI
│   ├── requirements.txt
│   └── Dockerfile
├── data/                    # Persistent storage (Mounted via Docker Volumes)
│   ├── mlflow/              
│   ├── redis/               
│   ├── uploaded_datasets/   
│   └── copilot.db           
├── docker-compose.yml
└── .env                     
```

---


## Prerequisites

### For Docker Setup (Recommended)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine (Linux)
- A **Groq API key** — free at [console.groq.com](https://console.groq.com)

### For Local Setup (Without Docker)
- Python 3.11+
- Redis server running locally
- A **Groq API key**

---

## Local Setup (Without Docker)

Follow these steps to run the project directly on your machine without Docker.

### Step 1 — Clone the Repository

```bash
git clone https://github.com/ThamaraBhagya/Data-Copilot.git
cd data-copilot
```

### Step 2 — Install Redis Locally

**Windows:**
Download and install from [github.com/microsoftarchive/redis/releases](https://github.com/microsoftarchive/redis/releases), then run:
```bash
redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install redis-server
sudo systemctl start redis
```

Verify Redis is running:
```bash
redis-cli ping
# Expected output: PONG
```

### Step 3 — Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 4 — Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 5 — Install Frontend Dependencies

```bash
cd ../frontend
pip install -r requirements.txt
```

### Step 6 — Configure Environment Variables

Create a `.env` file in the project root:

```bash
# From the project root
cp .env.example .env   # if example exists, otherwise create manually
```

Edit `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
MLFLOW_TRACKING_URI=http://localhost:5000
REDIS_URL=redis://localhost:6379
DATABASE_URL=sqlite:///./copilot.db
UPLOAD_DIR=uploaded_datasets
CHART_PATH=output_chart.png
```

### Step 7 — Start MLflow Tracking Server

Open a new terminal:

```bash
pip install mlflow
mlflow server --host 0.0.0.0 --port 5000
```

### Step 8 — Start the Backend

Open a new terminal, activate the virtual environment, then:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

You should see:
```
[DB] SQLite initialized ✅
[Cache] Redis connected ✅
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 9 — Start the Frontend

Open another terminal, activate the virtual environment, then:

```bash
cd frontend
streamlit run app.py
```

### Step 10 — Open the App

| Service | URL |
|---|---|
| **App** | http://localhost:8501 |
| **API Docs** | http://localhost:8000/docs |
| **MLflow** | http://localhost:5000 |

---

## Docker Setup

This is the recommended setup — runs all services with a single command.

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/data-copilot.git
cd data-copilot
```

### Step 2 — Configure Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

> Everything else is handled automatically by `docker-compose.yml`.

### Step 3 — Create Data Directories

```bash
mkdir -p data/uploaded_datasets data/redis data/mlflow
```

### Step 4 — Build and Start All Services

```bash
docker-compose up --build
```

Or run in the background:

```bash
docker-compose up --build -d
```

### Step 5 — Open the App

| Service | URL |
|---|---|
| **App** | http://localhost:8501 |
| **API Docs** | http://localhost:8000/docs |
| **MLflow** | http://localhost:5000 |



## Usage Guide

### 1. Upload a Dataset
- Click **Upload New CSV** in the sidebar
- Select any `.csv` file
- The file is saved but not loaded yet

### 2. Load a Dataset
- Select your uploaded file from the **Load a Dataset** dropdown
- Click **Load this dataset**
- An AI-generated summary appears with key columns, data quality notes, and 5 suggested questions

### 3. Ask Questions
Type any question in the chat input:
```
Show me a bar chart of sales by region
What is the average order value per customer?
Find the top 5 products by total revenue
Show correlation heatmap of all numeric columns
Which month had the highest number of orders?
```

### 4. Multi-CSV Join Mode
- Toggle **Multi-CSV Join Mode** in the sidebar
- Select 2 or more datasets
- Ask questions that span both datasets:
```
Join orders and customers on customer_id and show total revenue by country
```

### 5. Save and Replay Queries
- Click ⭐ on any response to save it to **Favourites**
- View past queries in the **Query History** panel
- Click ▶ on any history item to replay it

### 6. Export Results
- Click **⬇️ Download CSV** under any table result
- Click **⬇️ Download Chart** under any chart

---

## API Reference

Full interactive API docs available at: `http://localhost:8000/docs`

---

## Security

All LLM-generated Python code is executed inside a **RestrictedPython sandbox** with the following protections:

- **Import whitelist** — only `pandas`, `matplotlib`, `seaborn`, `math`, and `statistics` are allowed
- **No file system access** — `open()`, `os`, and file operations are blocked
- **No network access** — `requests`, `urllib`, and similar are blocked
- **No subprocess execution** — `subprocess`, `os.system` are blocked
- **Safe builtins only** — dangerous builtins like `eval()`, `exec()`, `compile()` are removed

> ⚠️ Despite sandboxing, do not expose this application to the public internet without additional authentication and hardening.

---

## Data Persistence

All data is stored in the `./data/` directory and survives container restarts:

| Location | Contents |
|---|---|
| `./data/uploaded_datasets/` | All uploaded CSV files |
| `./data/copilot.db` | SQLite — query history, favourites, dataset metadata |
| `./data/redis/` | Redis RDB snapshot |
| `./data/mlflow/` | MLflow experiment runs and artifacts |
| `./data/output_chart.png` | Most recently generated chart |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

---



