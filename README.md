# Research Agent

## Overview

Research Agent is an AI-powered application that performs web-based research, gathers information from multiple sources, and presents a consolidated answer with source references and confidence scoring.

The project demonstrates Agentic AI concepts including tool usage, web search, information retrieval, confidence estimation, and deployment.

---

## Features

* Web research from multiple sources
* Source collection and display
* Confidence scoring
* Streamlit user interface
* Railway deployment
* Dockerized application
* GitHub Actions CI pipeline

---

## Architecture

User Question

↓

Research Agent

↓

Search Web Sources

↓

Read Top Sources

↓

Aggregate Information

↓

Generate Response

↓

Confidence Score + Sources

---

## Tech Stack

* Python
* Streamlit
* Requests
* BeautifulSoup
* FastAPI
* Docker
* Railway
* GitHub Actions

---

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Streamlit:

```bash
streamlit run app.py
```

Start Health API:

```bash
uvicorn health_api:app --reload
```

---

## Health Check

```http
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

---

## Live Demo

Railway Deployment URL:

(Add your Railway URL here)

---

## Author

Khush Chheda
