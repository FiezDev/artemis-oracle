# Ittipol Vongapai

**Senior Full-Stack Engineer — React / Next.js · Node / Bun · GraphQL · AI Systems**

Bang Phli, Samut Prakan, Thailand · +66 91 721 0274 · itti.task@gmail.com  
GitHub: github.com/FiezDev · LinkedIn: linkedin.com/in/fiezdev · Portfolio: fiez.dev/portfolio  
Date of Birth: 11 November 1983 · Nationality: Thai  

---

## Professional Summary

Senior full-stack engineer with 5 years building production SaaS, multi-tenant platforms, and applied-AI systems for Thai enterprises. Currently Dev Lead of the developer team at Go Thailand, where I architect and ship an agritech IoT platform (RiceGuard) end-to-end — GraphQL API, operations dashboards, and the full AWS production infrastructure. I also build the supporting tooling — QC, dataset labeling and dashboards — for the AI team's vehicle and person-recognition models. Owner-class across the stack: PostgreSQL/Drizzle/MySQL data layers, Bun/Elysia/Node/Django APIs, and React 19/Next.js/Vue/React Native frontends. I design and build my own AI systems — LLM pipelines, multi-agent automation, and MCP servers — and the data and QC tooling that feeds the AI team's computer-vision models.

---

## Core Skills

**Languages:** TypeScript, JavaScript, Python, PHP, C#, SQL, Dart  
**Frontend:** React 19, Next.js (App Router), Vue 2/3, React Native, Flutter, Tailwind CSS, shadcn/ui, Radix UI, Zustand, TanStack Query, React Hook Form, Zod, Vitest, Jest  
**Backend:** Node.js, Bun, Elysia, Hono, Express, Django, .NET/C#, GraphQL (Apollo / Yoga), Drizzle ORM, Sequelize, REST, OAuth2, JWT  
**Databases:** PostgreSQL, TimescaleDB, MySQL, MongoDB / AWS DocumentDB, Redis  
**Cloud & DevOps:** AWS (EC2, RDS, S3, SES, SQS, DocumentDB), GCP, Vercel, Docker, GitHub Actions, Infrastructure-as-Code, PM2  
**AI & ML:** LLM pipelines, multi-agent automation, MCP servers, LangChain, Anthropic Claude, OpenAI, PyTorch, GroundingDINO / YOLO, pgvector / RAG  
**Practices:** Multi-tenant SaaS architecture, RBAC, TDD, idempotent migrations, code review, Agile (grooming / planning / retrospectives)  

---

## Professional Experience

### Go Thailand — Dev Lead, Developer Team (Contract, Remote)
*January 2025 – Present*

Lead the developer team building production platforms for a property and CCTV-AI vertical (Go Thailand / Mobile AI Co., Ltd.), and own systems end-to-end — from data layer to dashboards to cloud infrastructure.

- RiceGuard — agritech IoT + AI platform: built the operations, admin and AI-Ops dashboards and the GraphQL API (8 domains on PostgreSQL 16 + TimescaleDB), and designed the full AWS production infrastructure as code — VPC across two AZs, ALB/NLB, a RabbitMQ broker for MQTTS telemetry, EC2-hosted API, S3 and Secrets Manager, with GitHub Actions CI/CD.
- Built the supervisor QC and dataset-labeling tooling that supports the AI team's vehicle/person-recognition models (STAR Search Engine) — human-vs-AI verification, GroundingDINO/YOLO frame extraction, and vector-similarity dedupe — feeding their PyTorch/Roboflow training.
- Also delivered a multi-tenant CCTV/face-search SaaS (company-scoped data isolation, GPU orchestration over H200 + H100 servers) and a property/lease/tax SaaS with Thai tax compliance and accounting-system sync.

### 7Solutions Co., Ltd. — Senior Frontend Developer
*June 2024 – November 2024 · Bangkok*

- Senior frontend on LotteryPlus (lottery web app + back office) — planned a modern React/Next.js architecture (shadcn/ui, Tailwind, React Query, Zod), built a reusable component system, and drove code quality through reviews in Agile delivery.

### NestiFly — Assistant Manager / Full-Stack Developer
*September 2022 – May 2024 · Bangkok*

- Built the NestiFly CRM/API (Darkphoenix / Blackbird) end-to-end — architecture, database schema, APIs and UX/UI — and deployed the full stack to Google Cloud Platform.
- Maintained the Bluebird (Stocklend) React Native app across the App Store and Google Play with regular feature releases and refactors.

### Fusion Solution Co., Ltd. — Full-Stack Developer (Contract)
*March 2021 – April 2022 · Bangkok*

- Delivered client products across Vue, Flutter, AngularJS and C#/.NET — a Taxi-service app (navigation, driver ratings, admin CRUD) and a Health-Insurance web app (authentication, customer reports, coupon systems).

---

## Selected Projects

### AtEase — AI Content-Automation Platform
*Solo · production*

- Visual node-graph workflow builder that turns one idea into multi-platform posts — LLM drafting, fact-check, translate, image/video generation, and auto-publishing — run in the background by Hermes AI agents. Live behind the QOne AI News Facebook page.
- **Stack:** TypeScript · React · Bun · Node.js · LLMs · Playwright · PostgreSQL

### ORG-TOOLS — Internal Engineering Platform
*Team · internal*

- Turns Jira projects into versioned ISO documentation (LLM-drafted), with a knowledge-graph and pgvector semantic search, an Excel/CSV issue exporter, and zero-knowledge credential vaults (server stores only ciphertext).
- **Stack:** TypeScript · Bun · React · PostgreSQL · Jira API · AWS S3

### Vehicle Verifier — AI Classification QC Tool
*Internal*

- Supervisor review tool placing human labels beside AI predictions (type / color / make) with confidence scores, auto-flagged disagreements, and a reference-image panel for visual comparison against real vehicles.
- **Stack:** Next.js · React · TypeScript · PHP · AWS S3 · MySQL

### Image Crawler & Labelling — AI Dataset Pipeline
*Internal*

- End-to-end console for building AI training datasets — multi-provider crawling, MD5 + vector-similarity dedupe, keyboard-driven review, GroundingDINO + YOLO frame extraction, and one-click export to Roboflow; long jobs run in the background with live progress.
- **Stack:** Python · FastAPI · React · PyTorch · GroundingDINO · Roboflow · Redis · AWS S3


---

## Education & Continuous Learning

- Self-taught engineer — skills built through five years of production delivery and continuous, self-directed learning across the full stack, cloud, and applied AI.
- Secondary education, Thailand.

---

## Languages

Thai (native) · English (conversational & technical — communicates effectively)
