# Lantrn Agent Builder - Development Roadmap

## Project Overview

**Goal:** Build an on-premises deployable AI agent system for Mac Ultra + NAS
**Timeline:** 12 weeks to MVP
**Methodology:** BMad v6 Alpha (Plan → Build → Verify)

---

## Phase 1: Foundation (Weeks 1-3)

### Week 1: Core Infrastructure
- [ ] Project scaffolding (Python + FastAPI backend)
- [ ] Configuration system (YAML-based)
- [ ] Logging and tracing infrastructure
- [ ] Model adapter interface (Ollama first)
- [ ] Basic CLI with `lantrn init`, `lantrn plan`

### Week 2: Agent Runtime
- [ ] Agent definition parser (YAML/Markdown)
- [ ] Tool registry system
- [ ] Code execution sandbox
- [ ] Memory system (SQLite + vector store)
- [ ] Policy enforcement engine

### Week 3: BMad Role Chain
- [ ] Analyst agent implementation
- [ ] PM agent implementation
- [ ] Architect agent implementation
- [ ] Blueprint generation format
- [ ] Plan phase orchestration

---

## Phase 2: Execution Layer (Weeks 4-6)

### Week 4: Dev & QA Agents
- [ ] Dev agent implementation
- [ ] QA agent implementation
- [ ] Build phase orchestration
- [ ] Verify phase orchestration
- [ ] Test runner integration

### Week 5: Tool Suite
- [ ] Code execution tool (Python, Shell)
- [ ] File operations tool
- [ ] Document processing tool
- [ ] Browser agent tool
- [ ] API connector tool

### Week 6: Workspace Management
- [ ] Workspace isolation
- [ ] Multi-service support
- [ ] Context partitioning
- [ ] Run manifest generation
- [ ] Diff and change tracking

---

## Phase 3: User Interface (Weeks 7-8)

### Week 7: Web Dashboard
- [ ] React + TypeScript frontend
- [ ] Real-time execution view
- [ ] Blueprint editor
- [ ] Run history browser
- [ ] Settings management

### Week 8: Dashboard Features
- [ ] Agent configuration UI
- [ ] Policy editor
- [ ] Model profile management
- [ ] Log viewer
- [ ] Export/import workspaces

---

## Phase 4: On-Prem Deployment (Weeks 9-10)

### Week 9: Packaging
- [ ] Docker containerization
- [ ] Docker Compose stack
- [ ] NAS mount configuration
- [ ] Environment variable system
- [ ] Health checks and monitoring

### Week 10: Mac Ultra Optimization
- [ ] Metal acceleration for Ollama
- [ ] Memory optimization
- [ ] Auto-start scripts
- [ ] Backup/restore system
- [ ] Update mechanism

---

## Phase 5: Polish & Ship (Weeks 11-12)

### Week 11: Documentation & Testing
- [ ] User documentation
- [ ] API documentation
- [ ] Integration tests
- [ ] Performance benchmarks
- [ ] Security audit

### Week 12: Release
- [ ] Installation guide
- [ ] Quick start tutorial
- [ ] Example agents
- [ ] Customer deployment guide
- [ ] Support documentation

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, asyncio |
| Frontend | React 18, TypeScript, Tailwind |
| Database | SQLite (metadata), ChromaDB (vectors) |
| LLM | Ollama (primary), OpenAI/Anthropic (optional) |
| Execution | Docker, sandboxed subprocess |
| Deployment | Docker Compose, systemd |

---

## Success Metrics

### MVP Success
- [ ] Plan → Build → Verify pipeline works end-to-end
- [ ] All 5 BMad roles functional
- [ ] Local Ollama models work offline
- [ ] Dashboard shows real-time execution
- [ ] One-click deployment on Mac Ultra

### Customer Success
- [ ] Install time < 30 minutes
- [ ] First agent run < 5 minutes from install
- [ ] Zero external API calls required
- [ ] Full audit trail of all operations

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Ollama performance on Mac | Test early with M2 Ultra, optimize model selection |
| Memory constraints | Implement context windowing, disk-backed memory |
| Security vulnerabilities | Sandbox all execution, enforce policies |
| Customer deployment issues | Comprehensive install guide, remote diagnostics |

---

*Roadmap created: 2026-02-23*
*Target MVP: 12 weeks*
