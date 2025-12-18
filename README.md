# LLM-Black-Box

**LLM Black Box**
*End-to-End Observability for LLM Applications using Datadog & Google Vertex AI*

---

## 📌 Overview

Large Language Models (LLMs) introduce new operational challenges that traditional monitoring tools were not designed to handle. Unlike deterministic software systems, LLM-powered applications can fail silently, degrade in quality, spike in cost, or generate unsafe outputs without raising conventional errors.

**LLM Black Box** is a reference implementation of a production-ready observability strategy for LLM applications. It demonstrates how to monitor, detect, and respond to issues in an AI system using **Datadog** and **Google Vertex AI (Gemini)**.

This project implements a simple LLM-powered application and instruments it end-to-end to surface latency, errors, cost signals, and safety risks — transforming opaque AI behavior into actionable engineering insights.

---

## 🎯 Problem Statement

Organizations deploying LLMs in production face several challenges:

* Lack of visibility into model behavior and performance
* Silent failures where outputs appear valid but are incorrect
* Unpredictable latency impacting user experience
* Token and cost explosions without warning
* Safety and compliance risks due to hallucinations or unsafe responses
* No clear incident response workflow for AI failures

Traditional observability tools focus on infrastructure and APIs, not AI behavior.

---

## 💡 Solution

**LLM Black Box** provides an end-to-end observability framework for LLM applications by:

* Capturing LLM-specific telemetry (latency, tokens, prompts, responses)
* Streaming runtime telemetry to Datadog
* Defining detection rules for abnormal behavior
* Automatically creating actionable incidents with context
* Visualizing system health through dashboards and SLOs

This approach treats the LLM as a first-class production system, not a black box.

---

## 🧠 What This Application Does

The application exposes a simple AI-powered endpoint:

1. A user submits a question
2. The backend sends the prompt to Gemini (Vertex AI)
3. The model generates a response
4. The application emits observability data to Datadog

The focus is not the AI use case itself, but how the system is observed, monitored, and operated.

---

## 🏗️ Architecture

```
User
  ↓
Frontend (HTML)
  ↓
FastAPI Backend (Python)
  ↓
Google Vertex AI (Gemini)
  ↓
Telemetry Pipeline
  ├── Logs
  ├── Traces (APM)
  ├── Metrics
  ↓
Datadog
  ├── Dashboards
  ├── Detection Rules (Monitors)
  ├── SLOs
  └── Incident Management
```

---

## 🛠️ Technologies Used

| Technology                  | Purpose                |
| --------------------------- | ---------------------- |
| Google Vertex AI (Gemini)   | Hosted LLM             |
| FastAPI (Python)            | Backend API            |
| Datadog                     | Observability platform |
| Datadog APM                 | Distributed tracing    |
| Datadog Logs                | LLM telemetry          |
| Datadog Monitors            | Detection rules        |
| Datadog Incident Management | Actionable alerts      |
| Google Cloud Run            | Serverless hosting     |
| HTML / JavaScript           | Lightweight frontend   |

All components can be run using free tiers or trial accounts.

---

## 📊 Observability Strategy

### Signals Collected

| Signal                  | Description              |
| ----------------------- | ------------------------ |
| Request latency         | End-to-end response time |
| Error rate              | Application failures     |
| Prompt length           | Input size               |
| Response length         | Output size              |
| Token usage (estimated) | Cost indicator           |
| Model name              | Debugging & comparison   |
| Safety flags            | Risk detection           |

---

## 🚨 Detection Rules

The following detection rules are configured in Datadog:

### 1. High Latency Monitor

* **Condition**: p95 latency > 3 seconds
* **Purpose**: Detect degraded user experience

### 2. Error Rate Monitor

* **Condition**: Error rate > 5%
* **Purpose**: Detect application instability

### 3. Token Usage Spike Monitor

* **Condition**: Average token usage exceeds threshold
* **Purpose**: Prevent unexpected cost increases

### 4. Unsafe Response Monitor

* **Condition**: Safety flag detected in LLM output
* **Purpose**: Surface compliance and risk issues

---

## 🚑 Incident Management Workflow

When a detection rule is triggered:

1. Datadog Monitor enters alert state
2. A Datadog Incident is automatically created

The incident includes:

* Triggering monitor
* Timeline of events
* Sample traces and logs
* A runbook with remediation steps

Engineers use the context to diagnose and resolve the issue.
The incident resolves automatically once metrics return to normal.

---

## 📈 Dashboards & SLOs

The Datadog dashboard provides:

* Application latency (p50, p95)
* Error rate over time
* Token usage trends
* Monitor and incident status
* Request throughput

SLOs define expected reliability targets and surface error budgets.

---

## 🚦 Traffic Generator

A simple script is included to generate load and demonstrate detection rules:

```python
import requests

URL = "https://your-cloud-run-url/ask"

for _ in range(50):
    requests.post(URL, json={
        "question": "Explain cloud computing in detail"
    })
```

This script can be used to intentionally trigger latency and token-based alerts.

---

## 🚀 Deployment

### Backend

* Hosted on Google Cloud Run
* Serverless, scalable, free tier compatible

### Frontend

* Served via the same backend or GitHub Pages

---

## 📂 Repository Structure

```
.
├── app/
│   ├── main.py            # FastAPI application
│   ├── llm.py             # Gemini integration
│   └── observability.py   # Datadog logging & tracing
├── frontend/
│   └── index.html
├── traffic/
│   └── generate_load.py
├── datadog/
│   ├── dashboards.json
│   ├── monitors.json
│   └── slos.json
├── README.md
├── LICENSE
└── requirements.txt
```

---

## 📦 Running Locally

```bash
pip install -r requirements.txt
DD_SERVICE=llm-blackbox ddtrace-run uvicorn app.main:app
```

---

## 🔐 License

This project is licensed under the **MIT License**.

---

## 🎥 Demo Video

A 3-minute walkthrough demonstrates:

* Observability strategy
* Detection rules
* Incident creation
* Dashboard views

---

## 🏁 Conclusion

**LLM Black Box** demonstrates how to operate AI systems with the same rigor as traditional production software. By combining Google Vertex AI with Datadog observability, this project turns opaque model behavior into measurable, actionable signals — enabling safer, more reliable, and more cost-effective AI applications.

---

## 📬 Contact

For questions or contributions, feel free to open an issue or pull request.

**Built for the Datadog Challenge — AI Partner Catalyst Hackathon**
