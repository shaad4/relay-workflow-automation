<div align="center">

<img src="https://res.cloudinary.com/dltvyhamc/image/upload/f_auto/q_auto/relay-light_xunkgh.png" alt="Relay logo" width="400" />

### Intelligent Workflow Automation Platform

**Event → Understand → Retrieve Knowledge → Decide → Validate → Act → Observe → Recover**

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Kafka](https://img.shields.io/badge/Kafka-231F20?style=for-the-badge&logo=apachekafka&logoColor=white)](https://kafka.apache.org/)
[![gRPC](https://img.shields.io/badge/gRPC-244c5a?style=for-the-badge&logo=grpc&logoColor=white)](https://grpc.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)

</div>

---

## 🚀 What is Relay?

Relay is a **multi-tenant workflow automation platform** for processes that are too complex for a simple `Event → Action` rule. A company builds a workflow once in a visual editor, publishes it, and Relay runs it whenever the trigger fires — pulling data from APIs, retrieving company knowledge with **RAG**, making **structured AI decisions**, asking for **human approval**, and **recovering** when something fails .. .

> Relay never moves money itself. It calls the payment provider's API; the provider performs the refund.

## ✨ Key Features

| | |
|---|---|
| 🎨 **Visual workflow builder** | Drag-and-drop nodes, data mapping with `{{variables}}`, test & publish |
| 🪝 **Dynamic webhooks** | Per-workflow endpoint, secret auth, instant `202 Accepted` |
| 📚 **RAG knowledge base** | Upload docs → chunk → embed → pgvector search, tenant-scoped |
| 🤖 **Controlled AI decisions** | Strict output schema + Pydantic validation before any action runs |
| 🙋 **Human approval** | Pause, wait for a decision, resume |
| 🛡️ **Reliability** | Retries with backoff, idempotency keys, dead-letter queue, replay |
| 🔍 **Observability** | Step-level execution history and audit logs |
| 🔒 **Security** | Argon2id, JWT, RBAC, workspace isolation, credentials never exposed |

## 🏗️ Architecture

True microservices, each owning its own database. Three communication layers: **REST** (external), **gRPC** (internal sync), **Kafka** (async events).

```mermaid
flowchart TB
    FE["🖥️ Frontend<br/>Next.js"] -->|REST| GW["🚪 API Gateway"]
    EXT["🌐 External Systems"] -->|"POST /hooks/{token}"| INT

    GW --> AUTH["🔐 Auth"]
    GW --> WF["🧩 Workflow"]
    GW --> INT["🪝 Integration"]
    GW --> RAG["📚 RAG"]
    GW --> EXE["⚙️ Execution"]

    INT ==>|"Kafka: workflow.triggered"| K{{"📨 Kafka"}}
    K ==> EXE

    EXE -.->|gRPC| WF
    EXE -.->|gRPC| RAG
    EXE -.->|gRPC| ACT["🔌 Action"]
    EXE -.->|gRPC| AUTH

    ACT -->|HTTPS| PROV["🏦 Providers<br/>Stripe · Email · APIs"]

    classDef svc fill:#eef2ff,stroke:#6366f1,stroke-width:2px,color:#1e1b4b;
    classDef bus fill:#fff7ed,stroke:#ea580c,stroke-width:2px,color:#7c2d12;
    class GW,AUTH,WF,INT,RAG,EXE,ACT svc;
    class K bus;
```

| Service | Owns | Responsibility |
|---|---|---|
| 🚪 API Gateway | — | Routing, auth context, rate limiting |
| 🔐 Auth | users, workspaces | Identity & permissions |
| 🧩 Workflow | workflows, versions, nodes, edges | Definitions, validation, publishing |
| 🪝 Integration | webhooks | Webhook registration & ingestion |
| 📚 RAG | knowledge bases, documents, chunks | Ingestion & vector retrieval |
| ⚙️ Execution | executions, steps, approvals, idempotency, DLQ | Orchestration & reliability |
| 🔌 Action | connections | Connectors & external side effects |
| 📝 Audit | audit logs | Audit events |

## 🔄 How a Workflow Runs

```mermaid
sequenceDiagram
    autonumber
    participant EXT as 🌐 External System
    participant INT as 🪝 Integration
    participant K as 📨 Kafka
    participant EXE as ⚙️ Execution
    participant WF as 🧩 Workflow
    participant RAG as 📚 RAG
    participant ACT as 🔌 Action

    EXT->>INT: POST /hooks/{token}
    INT->>K: workflow.triggered
    INT-->>EXT: 202 Accepted
    K->>EXE: consume event
    EXE->>WF: gRPC GetPublishedVersion
    loop each node
        EXE->>RAG: gRPC Retrieve (RAG nodes)
        EXE->>ACT: gRPC ExecuteAction (+ idempotency key)
        EXE->>K: step completed / failed
    end
    EXE->>K: workflow.completed
```

## 🧾 Example: Refund Automation

```mermaid
flowchart LR
    W["🪝 Webhook"] --> GO["🌐 Get Order"] --> RG["📚 RAG: Policy"] --> AI["🤖 AI Decision"] --> C{"Condition"}
    C -- APPROVE --> RF["💳 Refund"] --> EM["✉️ Email"]
    C -- REJECT --> RJ["✉️ Rejection"]
    C -- REVIEW --> HA["🙋 Approval"]
    HA --> RF
```

## 🛡️ Reliability

```mermaid
flowchart LR
    S["Execute step"] --> R{"Success?"}
    R -- Yes --> N["Next node"]
    R -- "No, retryable" --> B["Backoff 1s → 2s → 4s"] --> S
    R -- "No, exhausted" --> DLQ[("☠️ DLQ")] --> OP["Replay / Resolve"]
```

Duplicate events are blocked by per-workspace **idempotency keys**. Published workflow versions are **immutable**, so running executions are never affected by edits.

## 🧰 Tech Stack

**Backend** Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic v2 · Alembic  
**Data** PostgreSQL · pgvector · Redis (optional)  
**Messaging** Apache Kafka · gRPC + Protobuf  
**Frontend** React / Next.js  
**Infra** Docker Compose · GitHub Actions · Pytest

## 📁 Structure

```text
relay/
├── services/   # api-gateway, auth, workflow, integration, rag, execution, action, audit
├── proto/      # gRPC contracts
├── packages/   # shared config, event schemas, observability
├── frontend/
├── infrastructure/
├── tests/
└── docker-compose.yml
```

## ⚡ Quick Start

```bash
git clone https://github.com/<your-username>/relay.git
cd relay
cp .env.example .env
docker compose up --build
```

## 🗺️ Roadmap

- [x] Architecture & service design
- [ ] **Week 1** — Auth, workspaces, workflow model, service skeletons
- [ ] **Week 2** — Webhooks, connections, actions, human approval
- [ ] **Week 3** — RAG pipeline & structured AI decisions
- [ ] **Week 4** — Kafka workers, retries, idempotency, DLQ, dashboard

**Later:** more connectors & triggers · OAuth · workflow templates · failed-step replay · tracing

## 📄 License

MIT — see [`LICENSE`](LICENSE).

<div align="center">

⭐ **Star the repo if you find Relay interesting!** ⭐

</div>
