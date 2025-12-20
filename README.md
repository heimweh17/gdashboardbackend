# GeoDashboard Backend

**FastAPI-based Geospatial Analytics & AI Insight Backend**

This repository contains the backend system for **GeoDashboard**, a full-stack geospatial analytics platform focused on spatial analysis, system design, and responsible AI integration.

The backend handles authentication, dataset ingestion, geospatial analytics, and AI-assisted analytical insights in a production-style environment.

---

## Key Features

- FastAPI backend with JWT authentication  
- PostgreSQL + SQLAlchemy ORM  
- Deterministic geospatial analysis (density, clustering, aggregation)  
- AI-powered analytical insights with strict per-user rate limits  
- Dockerized deployment on Railway  
- Lightweight CI pipeline (GitHub Actions)

---

## Architecture

The system is designed with a **service-oriented architecture**:

- **Core Backend Service**
  - Authentication, datasets, spatial analysis, persistence
- **AI Insight Service**
  - Dedicated service for LLM-based analytical summaries
  - Isolated to control cost, latency, and reliability

This separation enables scalability, fault isolation, and responsible AI usage.

---

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker
- Google Gemini (AI insights)
- GitHub Actions (CI)

---

## Main Project

This backend powers the full GeoDashboard platform.

🔗 **Main Repository:**  
https://github.com/heimweh17/Geo-Dashboard

🔗 **Live Demo:**  
https://thegeodashboard.vercel.app/

---

## Author

**Alex Liu**  
Computer Science @ University of Florida  

https://aliu.me  
https://github.com/heimweh17
