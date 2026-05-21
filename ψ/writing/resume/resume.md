# Ittipol Vongapai

**Full-Stack Developer | AI Automation & Agentic AI Enthusiast | React, Next.js, TypeScript | Node.js, Bun, GraphQL, PostgreSQL | LangChain, Claude, MCP**

Bang Phli, Samut Prakan, Thailand · +66 91 721 0274 · itti.task@gmail.com
GitHub: github.com/FiezDev · LinkedIn: linkedin.com/in/fiezdev · Portfolio: fiez.dev/portfolio

---

## Professional Summary

Full-stack developer with 5 years of experience building production SaaS, multi-tenant platforms, and AI-driven systems for Thai enterprises. Strong **interest in AI automation and agentic AI** — actively building a 20-agent AI workforce platform (QOne Corp), an AI persona framework with MCP server integrations (Artemis Oracle), and a CNN-based vehicle classifier. Owner-class contributor across the full stack — from PostgreSQL/Drizzle/MySQL data layers and Bun/Elysia/Node/Django APIs to React 19 / Next.js 16 / Vue / React Native frontends with Tailwind, Zustand, and TanStack Query. Strong analytical skills and proactive attitude drive my commitment to delivering high-quality solutions, improving code quality, and exploring new technology options. Currently a Go Thailand contractor leading multiple concurrent enterprise products including a multi-tenant CCTV/face-search SaaS, a Thai property/tax SaaS, an agricultural IoT GraphQL platform, and a 100%-coverage FlowAccount middleware. **2,094 GitHub contributions in 2025** and **1,715 YTD in 2026** across 16 active repositories.

---

## Top Skills

JavaScript · Tailwind CSS · React Native · Python · Django

## Core Skills

**Languages:** JavaScript, TypeScript, Python, PHP, C#, SQL, Dart
**Frontend:** React 19, Next.js 14/16 (App Router), Vue.js (2/3), React Native, Flutter, AngularJS, Tailwind CSS, shadcn/ui, Radix UI, PrimeNG, Vuetify, NativeBase, Zustand, TanStack Query, React Hook Form, Zod, Storybook, Cypress, Vitest, Jest
**Backend:** Node.js, Bun, Elysia, Express, Hono, Sequelize ORM, Drizzle ORM, GraphQL Yoga, Django, .NET / C#, REST, OAuth2, JWT
**Databases:** PostgreSQL, TimescaleDB, MySQL, MongoDB / AWS DocumentDB, Redis (ioredis), Firebase Firestore
**Cloud / DevOps:** AWS (EC2, RDS, S3, SES, SQS, DocumentDB), GCP, Vercel, Docker / Docker Compose, GitHub Actions → GHCR, PM2, DevContainer
**Messaging / Realtime:** RabbitMQ, Socket.io, Firebase Cloud Messaging, LINE Messaging API, LIFF, Server-Sent Events
**AI / ML / Tooling:** PyTorch (ResNet-18), AWS S3 SigV4, LangChain, Anthropic Claude, OpenAI, GLM agentic systems, ChromaDB + FTS5 hybrid search, Claude Code SDK, MCP servers
**Practices:** Analytical thinking, attention to detail, TDD, multi-tenant SaaS architecture, RBAC, workflow engines, idempotent migrations, conventional commits, Agile (grooming/planning/retrospectives), code review

---

## Professional Experience

### Go Thailand — Full Stack Engineer (Contract, Remote)
**January 2025 – Present**

Lead engineer across **four concurrent enterprise products** for a Thai property and CCTV-AI vertical, delivered for Go Thailand and its sister entity Mobile AI Co., Ltd. **609 backend + 707 frontend commits on NT-TAG-ID alone**; 345 commits on DAD Asset Management; 89 sole-author commits on FlowAccount middleware.

- Developed and maintained scalable web applications using both front-end (Vue.js, React.js, Next.js) and back-end (PHP, Python, Node.js, Bun, Elysia) technologies.
- Designed and implemented robust system architectures and APIs capable of handling high data volumes and concurrent users, leveraging cloud services (AWS RDS, S3, SES, SQS, DocumentDB, EC2; GCP).
- Translated product requirements into technical designs and developed new features and functionalities accordingly.
- Contributed to system architecture decisions and provided constructive feedback within the development team.
- Analyzed application performance, identified bottlenecks, and implemented optimizations to enhance stability and user experience.

**NT-TAG-ID Platform (multi-tenant CCTV / face-search SaaS, api-core.nttagid.com / qms.nttagid.com)**
- Architected and operated a backend with **70+ MySQL tables, 82 Sequelize models, 77 routes, and 97 services**; onboarded **14 of 16 broker tenants** with company-scoped data isolation, phone-OTP login, and admin authorization tiers.
- Built the QMS GPU orchestration layer (PHP 8 + MySQL + Redis + Socket.io) managing **2 production GPU servers** (Kaytus H200 8-GPU + NT H100); refactored hardcoded GPU server values to a database-driven table and shipped a **4-hour rolling GPU stats history API** powered by Redis ZSETs.
- Migrated frontend from Vue 2 to **React 19 + Vite + Radix UI + Tailwind + TanStack Table + LIFF** with a strict two-layer architecture (shadcn primitives in `components/ui/` vs. themed wrappers in `components/theme-ui/`).

**Vehicle Classification AI Pipeline (NT-TAG-ID Vision)**
- Built a complete human-in-the-loop labeling + QC + training pipeline against **108,507 vehicle label rows** with a 4-person team leaderboard and per-labeler accuracy.
- Designed an MD5(track_id) deterministic **70/15/15 train/val/test split (37,872 / 8,115 / 8,116 tracks)** over a **54,802-image, 1.8 GB dataset** across 567 video segments for ResNet-18 training in PyTorch.
- Goal: replace rule-based color classifier that mis-labels **45% of vehicles as "blue"** (CCTV blue-shift artefact) with a CNN targeting **<20% blue rate — a 25-point absolute reduction** in misclassification.

**DAD Asset Management System (Thai property/lease/tax SaaS — dadassets.com)**
- Built **61 frontend pages and 126 backend service files** as full-stack lead — **1,210 commits in ~6 months** — for a Next.js 14 + Elysia + Bun + Drizzle + MySQL/AWS RDS application covering asset registers (land, buildings, vehicles, jewelry), lease management, document OCR, and Thai tax compliance (land/structure tax, signage tax, withholding tax).
- Implemented **full FlowAccount sync pipeline**: contact taxId fallback, billing PDF generation, monthly/annual aggregate tax reports.

**RiceGuard — Agricultural IoT GraphQL Platform (Mobile AI Co., Ltd. partnership)**
- Designed Domain-Driven Design layered architecture (model / queries / resolver triad) for the Rice-Guard-API GraphQL service — enforced as a contract so every new domain follows the same shape.
- Shipped **8 production GraphQL domains** backed by **44 idempotent SQL migrations** on PostgreSQL 16 + TimescaleDB hypertables for sensor readings and audit logs across **13 sister microservice repositories**.
- Built a **4-tier priority alert system with 3-queue RabbitMQ fan-out** (FCM, LINE, SSE) — single producer, parallel notification delivery — eliminating head-of-line blocking between channels.
- Implemented **RBAC with 4 roles** (admin / manager / farmer / viewer) and a LINE LIFF survey app integrated with the FCM push pipeline.

**FlowAccount Middleware (Bun + Elysia OAuth2 proxy)**
- Solo-built and shipped to production with **100% FlowAccount API coverage — 75 endpoints across 5 document types**, OAuth2 token caching, multi-tenant credential storage, and auto-retry on 401 Unauthorized.

**Stack:** React.js · Vue.js · Next.js · Node.js · Bun · Elysia · PHP · Python · Django · TypeScript · GraphQL Yoga · Drizzle ORM · Sequelize · PostgreSQL · TimescaleDB · MySQL · MongoDB · Redis · RabbitMQ · AWS · Tailwind CSS

---

### 7Solutions Company Limited — Senior Frontend Developer (Full-time, Hybrid)
**June 2024 – November 2024 · Bangkok, Thailand**

Senior frontend developer on **LotteryPlus** (Lottery Service WebApp + BackOffice).

- Collaborated with the team to plan and implement a modern stack and libraries for **React and Next.js**, including Zod, shadcn/ui, Tailwind CSS, react-query, and react-hook-form.
- Participated in planning and structuring components and managing overall application architecture.
- Engaged in **Agile workflows** including grooming, planning, and retrospectives.
- Collected requirements from the UX/UI team and designed features to meet their needs.
- Refined code to meet company standards and best practices.
- Conducted **code reviews** and provided input to improve overall codebase quality.

**Stack:** React · Next.js · TypeScript · Zustand · Zod · Tailwind CSS · shadcn/ui · React Hook Form

---

### NestiFly — Assistant Manager / Full Stack Developer (Full-time, Hybrid)
**September 2022 – May 2024 · 1 yr 9 mos · Bangkok, Thailand**

- Developed software, planned implementation steps, and worked across both Front-End and Full-Stack engineering.
- Coordinated with the **product team, UX/UI team, and various departments** to gather information for software development.
- Tested software to identify and resolve issues and bugs.
- Improved code quality, code structure, and database architecture for maximum software efficiency.
- Performed QA and deployed software systems as assigned.
- Researched, suggested, and provided information about new processes and technologies to improve work efficiency.
- Shared knowledge within the team as assigned.

**NestiFly CRM/API (Darkphoenix · Blackbird)**
- Built the project architecture and UX/UI from scratch to production-ready state.
- Revised database schema, refactored existing code, developed APIs, and **deployed the full stack to Google Cloud Platform** to enhance workflow efficiency and system effectiveness.

**Bluebird (Stocklend Application)**
- Maintained the **React Native** application across App Store and Google Play including tester licensing and test environment setup.
- Consistently rolled out features and refactored code to optimize user experience.

**Stack:** Python · Django · jQuery · DataTables · Tailwind CSS · MySQL · GCP · React · React Native · NativeBase · JavaScript

---

### Career Break
**May 2022 – September 2022 · 5 mos · Samut Prakan, Thailand**

Personal development and skill consolidation.

---

### Fusion Solution Co., Ltd. — Full Stack Developer (Contract)
**March 2021 – April 2022 · 1 yr 2 mos · Bangkok, Thailand**

- Developed the **front-end for web and mobile applications** in line with provided UI designs.
- Collected business requirements, delineated data sources, and defined data flow structures.
- Troubleshot and resolved issues impacting application usability.
- Architected and developed both backend and frontend components per customer specifications.

**Project — Short URL Service Website (Vue.js · C# · MySQL)**
- Collaborated intensively with UX/UI designers to build both Frontend and Backend of the ADMIN panel tailored for corporate clients.

**Project — Taxi Service App (Flutter · Vue.js)**
- Implemented front-end features such as Navigation and Driver Reviews.
- Created front-end widgets as designed in Adobe XD across various application features.
- Introduced **CRUD operations for Driver/Car data** in the ADMIN panel.

**Project — Health Insurance WebApp (AngularJS · C# · MySQL)**
- Debugged and maintained existing application features.
- Resolved UI and responsiveness bugs.
- Implemented new features including **Authentication, Customer Reports, and Coupon Codes**.
- Provided customer support concerning application issues and feature queries.

**Stack:** Vue.js · AngularJS · TypeScript · Flutter · C# · .NET · MySQL · Firebase · Vuetify · PrimeNG

---

## Selected Personal Projects

### QOne Corp — Multi-Agent AI Workforce Platform
**Solo · April 2026 – Present · 186 commits in 5 weeks**

- Designed and built a **20-specialized-agent workforce platform** with a custom **TaskNet v3.0 protocol** chain of command (CEO → Artemis → Division Lead → Division Agent).
- Built a **workflow engine** with 4 node types (process / conditional / sub_workflow / trigger), iteration fan-out, cancel cascade, depth limits, and a reaper for stuck children.
- Built a **Universal Source Resolver Registry — 29 Tier-1 resolvers** with Zod validation and SSRF defense.
- Built a **natural-language → cron translator** with a 60s-tick scheduler, **PostgreSQL advisory lock for multi-replica safety**, and a 24h backlog cap.
- Authored **The 10 Laws of Easy-to-Use UX** plus a custom `no-jargon` ESLint rule banning technical jargon in user-facing strings.
- 31 SQL migrations · 16 Drizzle schema modules · 14 dashboard sub-app routes · TimescaleDB hypertables on `agent_heartbeats` and `task_events`.
- **Stack:** Bun · Hono · Drizzle ORM · PostgreSQL · Next.js 14 · TanStack Query · Tailwind 4

### Artemis Oracle — Knowledge Management & AI Persona Framework
**Solo · March 2026 – Present · public**
- Knowledge-management monorepo built around five operating principles, powering an AI persona for personal project management.
- Integrated Arra Oracle MCP (FTS5 + ChromaDB hybrid search), Context7, Atlassian, and Pencil MCP servers.

### Portnext — Personal Portfolio (fiez.dev/portfolio)
**Solo · August 2022 – Present · public**
- **Stack:** Next.js 16 · TypeScript · React 19 · Tailwind 4 · Zustand · TanStack Query · React Hook Form · Zod · Firebase · Three.js · Storybook · Jest · Bun

### FlightClone — Amadeus Flight Search (flight.fiez.dev)
**Solo · 2024 · public** — React · TypeScript · MUI · Zod · nuqs · React Query · React Hook Form

### git-doc — Yearly Git Activity Summarizer
**Solo · December 2025 · public** — TypeScript CLI generating Excel reports with AI-powered summaries.

---

## GitHub Activity (Verified)

| Year | Total Contributions | Commits | Pull Requests | Repositories |
|------|--------------------:|--------:|--------------:|-------------:|
| 2026 (YTD May) | **1,715** | 1,661 | 20 | 16 |
| 2025 | **2,094** | 1,958 | 46 | 12 |
| 2024 | 237 | 153 | 0 | 20 |
| 2023 | 525 | 24 | 0 | 1 |
| 2022 | 234 | 187 | 3 | 3 |

**342 LinkedIn connections · 365 followers**

---

## Education

*[School name TBD] — Degree, Field of Study*
**2023 – Present (in progress)**

---

## Languages

- **Thai** — Native
- **English** — Professional working proficiency

---

## Interests

Generative AI agentic systems · Multi-agent workflow design · Developer experience · Knowledge management · Mobile MOBA · Basketball · Motorcycles
