# ShortList AI

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![React](https://img.shields.io/badge/React-18.x-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-purple)
![License](https://img.shields.io/badge/license-MIT-green)

**ShortList AI** is an intelligent multi-agent hiring platform that uses sequential AI decision-making to evaluate candidates fairly and efficiently. By combining a LangGraph-based reasoning pipeline, a FastAPI backend, and a React frontend, ShortList AI automates resume screening, generates explainable match scores, and provides real-time feedback to recruiters and candidates.

**Repository:** https://github.com/shreyamane1526/ShortListAI

---

# 📌 Table of Contents

* Problem Statement
* The Solution
* System Architecture
* Technology Stack
* Project Structure
* Key Features
* Getting Started
* Development Guide
* Testing
* Deployment
* Implementation Roadmap
* Future Scope
* Contributing
* License

---

# 🚨 Problem Statement

Traditional hiring systems face major challenges:

* Bad hires cost companies over **$17,000** on average.
* ATS systems reject many qualified candidates.
* Hiring often relies on keyword matching instead of actual skills.
* Neurodivergent candidates are frequently overlooked.

ShortList AI shifts hiring from keyword-based filtering to a **skills-first, transparent, and fair evaluation process**.

---

# 💡 The Solution

ShortList AI replaces traditional resume screening with a transparent multi-agent workflow:

1. Candidate applies for a position.
2. LangGraph orchestrates multiple AI agents.
3. Resume and job description are analyzed.
4. Candidate receives a match score and detailed explanation.
5. Recruiters review results and take action.
6. Real-time updates notify both recruiters and candidates.

Every decision is:

* Explainable
* Auditable
* Bias-aware

---

# 🧠 System Architecture

```mermaid
flowchart TD
    A([🧑 Candidate]) -->|Applies| B

    B["**FastAPI Backend**\nReceives & routes requests"]
    B -->|Triggers| C

    C["**LangGraph Orchestrator**\nCoordinates all AI agents"]

    C --> D["**Resume Parser**\nExtracts structured data"]
    C --> E["**JD Analyzer**\nDecodes requirements"]
    C --> F["**Skill Matcher**\nMaps skills to role"]
    C --> G["**Experience Evaluator**\nAssesses work history"]
    C --> H["**Cultural Fit Agent**\nValues alignment"]
    C --> I["**Explanation Generator**\nGenerates reasoning"]

    D --> J[("**Qdrant**\nVector store\nSemantic embeddings")]
    E --> J
    F --> J
    G --> J
    H --> J

    I --> K[("**PostgreSQL**\nDecisions & results")]

    K --> L["**Recruiter Dashboard**\nReview & shortlist"]
    K --> M["**Candidate Dashboard**\nStatus & feedback"]

    L -->|"Shortlist / Reject"| B

    %% Styles
    classDef infra    fill:#E6F1FB,stroke:#185FA5,color:#0C447C
    classDef orch     fill:#EEEDFE,stroke:#534AB7,color:#3C3489
    classDef agent    fill:#E1F5EE,stroke:#0F6E56,color:#085041
    classDef genagent fill:#FAECE7,stroke:#993C1D,color:#712B13
    classDef store    fill:#E6F1FB,stroke:#185FA5,color:#0C447C
    classDef dash     fill:#FAEEDA,stroke:#854F0B,color:#633806
    classDef actor    fill:#F1EFE8,stroke:#5F5E5A,color:#444441

    class A actor
    class B infra
    class C orch
    class D,E,F,G,H agent
    class I genagent
    class J,K store
    class L,M dash
```

---

## Component Overview

| Layer | Component | Role |
|---|---|---|
| **Entry** | Candidate | Submits application |
| **API** | FastAPI Backend | Receives requests, routes to orchestrator, applies recruiter decisions |
| **Orchestration** | LangGraph Orchestrator | Coordinates all AI agents in parallel |
| **Agents** | Resume Parser | Extracts structured candidate data from CV |
| | JD Analyzer | Decodes job description requirements |
| | Skill Matcher | Maps candidate skills to role requirements |
| | Experience Evaluator | Assesses depth and relevance of work history |
| | Cultural Fit Agent | Evaluates values and team alignment signals |
| | Explanation Generator | Produces human-readable reasoning for decisions |
| **Storage** | Qdrant Vector Store | Stores semantic embeddings for similarity search |
| | PostgreSQL | Persists decisions, scores, and results |
| **Output** | Recruiter Dashboard | Review shortlist, approve or reject candidates |
| | Candidate Dashboard | View application status and feedback |

---

## Data Flow

1. **Candidate applies** → FastAPI receives the submission
2. **FastAPI triggers** the LangGraph orchestrator
3. **Orchestrator fans out** to six agents running in parallel
4. **Five analytical agents** (Resume Parser, JD Analyzer, Skill Matcher, Experience Evaluator, Cultural Fit) write embeddings to **Qdrant**
5. **Explanation Generator** synthesises agent outputs and writes results to **PostgreSQL**
6. **Dashboards** read from PostgreSQL — recruiters see ranked shortlists, candidates see status
7. **Recruiter decisions** (shortlist / reject) feed back to FastAPI, closing the loop


### Components

| Component          | Purpose                           |
| ------------------ | --------------------------------- |
| FastAPI            | REST APIs and authentication      |
| LangGraph          | Multi-agent orchestration         |
| Qdrant             | Semantic similarity search        |
| PostgreSQL         | Persistent storage                |
| React + TypeScript | User interface                    |
| Redis              | Caching and background processing |

---

# 🛠 Technology Stack

| Area             | Technologies                                      |
| ---------------- | ------------------------------------------------- |
| Backend          | Python, FastAPI, SQLAlchemy, Pydantic, Alembic    |
| AI / ML          | LangGraph, LangChain, Groq LLaMA 3.3 70B, XGBoost |
| Vector Database  | Qdrant                                            |
| Database         | PostgreSQL                                        |
| Cache            | Redis                                             |
| Task Queue       | Celery, Temporal (planned)                        |
| Frontend         | React, TypeScript, Tailwind CSS                   |
| Authentication   | JWT                                               |
| Containerization | Docker, Docker Compose                            |
| Monitoring       | OpenTelemetry, Prometheus, Grafana                |
| Testing          | Pytest, Jest, React Testing Library               |

---

# 📁 Project Structure

```text
ShortListAI/
├── Backend/
│   ├── agents/
│   ├── api.py
│   ├── models.py
│   ├── run.py
│   ├── .env.example
│   └── test_evaluation_flow.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── App.tsx
│   └── package.json
│
├── ml/
├── orchestration/
├── repositories/
├── telemetry/
├── tests/
├── uploads/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

# ✨ Key Features

### Multi-Agent Evaluation Pipeline

* Resume Parser Agent
* Job Description Analyzer
* Skill Matcher
* Experience Evaluator
* Cultural Fit Agent
* Explanation Generator

### Explainable Match Scores

Every evaluation includes:

* Match score (0–100)
* Recommendation (YES / MAYBE / NO)
* Strengths
* Skill gaps
* Detailed reasoning

### Inclusive & Neurodiversity-Aware Hiring

ShortList AI is designed to promote fair opportunities for all candidates, including neurodivergent individuals.

* Focuses on skills and potential rather than keyword-heavy resumes
* Reduces bias caused by traditional ATS filtering
* Identifies transferable skills and non-traditional career paths
* Generates explainable evaluations instead of opaque rejections
* Encourages equitable candidate assessment through transparent AI reasoning
* Helps recruiters discover overlooked talent from diverse backgrounds

### Recruiter Dashboard

* Candidate ranking
* One-click shortlist/reject
* Evaluation insights
* Audit history

### Candidate Dashboard

* Application tracking
* Evaluation progress
* Recruiter feedback
* Real-time status updates

### Audit Trail

All evaluations and recruiter actions are logged for transparency.

### Dockerized Deployment

Run the entire platform locally with Docker Compose.

---

# 🚀 Getting Started

## Prerequisites

* Python 3.10+
* Node.js 18+
* Docker & Docker Compose
* PostgreSQL
* Groq API Key

---

## Clone Repository

```bash
git clone https://github.com/shreyamane1526/ShortListAI.git
cd ShortListAI
```

---

## Backend Setup

```bash
cd Backend

python -m venv venv

source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

Copy environment variables:

```bash
cp .env.example .env
```

Start backend:

```bash
python run.py
```

Backend runs on:

```text
http://localhost:5000
```

---

## Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

Frontend runs on:

```text
http://localhost:5173
```

---

## Docker Setup

```bash
docker-compose up --build
```

Services:

| Service  | URL                   |
| -------- | --------------------- |
| Frontend | http://localhost:3000 |
| Backend  | http://localhost:5000 |
| Qdrant   | http://localhost:6333 |

---

# 💻 Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/shortlistai
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=your_jwt_secret
REDIS_URL=redis://localhost:6379/0
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

---

# 🧪 Testing

## Backend Tests

```bash
cd Backend

python test_evaluation_flow.py
```

---

## Frontend Tests

```bash
cd frontend

npm test
npm run test:ci
```

---

# 🐳 Deployment

## Build Docker Image

```bash
docker build -t shortlistai:latest .
```

## Run Container

```bash
docker run \
-p 5000:5000 \
-p 3000:3000 \
--env-file Backend/.env \
shortlistai:latest
```

---

# 🗺 Roadmap

| Phase   | Focus                                 |
| ------- | ------------------------------------- |
| Phase 1 | Core Multi-Agent Platform             |
| Phase 2 | Distributed Infrastructure & Temporal |
| Phase 3 | Trust & Secure Architecture           |
| Phase 4 | Enterprise ML Lifecycle               |
| Phase 5 | Confidential AI & Enterprise Scale    |

---

# 🔮 Future Scope

### LinkedIn Integration

Real-time candidate ranking directly inside recruiter workflows.

### Multi-Tenant SaaS

Enterprise support with role-based access control and analytics.

### Predictive Retention Models

Forecast long-term employee retention and success.

### AI Interview Platform

Technical, HR, and behavioral interviews in multiple languages.

### Autonomous Hiring

Reduce recruiter screening effort by up to 80%.

---

# 🤝 Contributing

1. Fork the repository.
2. Create a feature branch.
3. Run tests.
4. Make changes.
5. Submit a pull request.

Before submitting:

```bash
python test_evaluation_flow.py
npm run build
```

Code Style:

* Python → Black
* TypeScript → Prettier



