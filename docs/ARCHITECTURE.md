# Lantrn Agent Builder - Architecture

## Overview

Lantrn Agent Builder is an on-premises deployable AI agent system that combines:
- **Agent Zero's** tool-based execution and subordinate delegation model
- **BMad v6 Alpha's** Plan → Build → Verify methodology with role chain

## Target Deployment

| Component | Specification |
|-----------|---------------|
| Primary Hardware | Mac Studio Ultra (M2/M3 Ultra) |
| Storage | NAS (Synology/QNAP) via SMB/NFS |
| Memory | 64GB+ RAM recommended |
| Network | Local LAN, optional VPN for remote access |

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LANTRN AGENT BUILDER                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   CLI/UI    │  │  Dashboard  │  │     API Gateway         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    ORCHESTRATION LAYER                     │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │  │
│  │  │ Analyst │ │   PM    │ │Architect│ │  Plan Registry  │  │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └─────────────────┘  │  │
│  │       └───────────┼───────────┘                            │  │
│  │                     ▼                                        │  │
│  │            ┌──────────────┐                                 │  │
│  │            │   BLUEPRINT   │                                │  │
│  │            └──────┬───────┘                                 │  │
│  └───────────────────┼─────────────────────────────────────────┘  │
│                      ▼                                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    EXECUTION LAYER                         │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────────────────────────┐  │  │
│  │  │   Dev   │ │   QA    │ │     Tool Registry           │  │  │
│  │  └────┬────┘ └────┬────┘ │  • Code Execution           │  │  │
│  │       │           │      │  • Browser Agent            │  │  │
│  │       │           │      │  • Document Processing      │  │  │
│  │       │           │      │  • File Operations          │  │  │
│  │       │           │      │  • API Connectors           │  │  │
│  │       └─────┬─────┘      └─────────────────────────────┘  │  │
│  │             ▼                                              │  │
│  │    ┌────────────────┐                                      │  │
│  │    │  VERIFICATION  │                                      │  │
│  │    └────────────────┘                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    INFRASTRUCTURE                          │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │  │
│  │  │   Memory    │ │  Policies   │ │    Model Adapters   │  │  │
│  │  │  (Vector +  │ │  (Guardrails)│ │  • Ollama (local)   │  │  │
│  │  │   SQLite)   │ │             │ │  • OpenAI           │  │  │
│  │  └─────────────┘ └─────────────┘ │  • Anthropic        │  │  │
│  │                                  │  • Venice AI        │  │  │
│  │                                  └─────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## BMad v6 Alpha Integration

### Two-Phase Pipeline

#### Phase 1: PLAN
1. **Analyst Agent** - Gathers requirements, analyzes context
2. **PM Agent** - Creates tasks, defines acceptance criteria
3. **Architect Agent** - Designs solution, specifies files/tools
4. **Output**: Blueprint (YAML manifest with tasks, files, tests, budgets)

#### Phase 2: BUILD & VERIFY
1. **Dev Agent** - Executes blueprint, writes code
2. **QA Agent** - Runs tests, validates acceptance criteria
3. **Output**: Manifest with traces, diffs, results

### Agent Definitions (agents/*.bmad.yaml)

```yaml
# Example: agents/analyst.bmad.yaml
role: analyst
objective: Gather and analyze requirements for agent tasks
inputs:
  - user_request
  - context_files
  - workspace_state
outputs:
  - requirements_doc
  - constraints
  - success_criteria
tools:
  - document_query
  - search_engine
  - code_execution_tool
model_profile: hq  # High-quality model for analysis
```

## Policy System (policies/org.yaml)

```yaml
# Default restrictive policy
version: "1.0"
name: default-policy

file_access:
  default: deny
  allow:
    - workspace/**
    - /tmp/**
  deny:
    - ~/.ssh/**
    - ~/.env
    - **/.credentials

network_access:
  default: deny
  allow:
    - api.openai.com
    - api.anthropic.com
    - ollama.local:11434
  deny:
    - "*"  # Deny all others

tool_access:
  default: allow
  deny:
    - input  # Require explicit approval for user input

budgets:
  max_tokens_per_task: 100000
  max_file_size_mb: 50
  max_execution_time_minutes: 30
```

## Workspace Structure

```
workspace/
├── .bmad/
│   ├── profiles/
│   │   ├── fast.yaml      # Quick, cheap model
│   │   ├── hq.yaml        # High-quality model
│   │   └── offline.yaml   # Local-only model
│   ├── blueprints/        # Plan outputs
│   └── runs/              # Execution manifests
├── agents/
│   ├── analyst.bmad.yaml
│   ├── pm.bmad.yaml
│   ├── architect.bmad.yaml
│   ├── dev.bmad.yaml
│   └── qa.bmad.yaml
├── policies/
│   └── org.yaml
├── services/
│   ├── core/              # Core agent runtime
│   ├── api/               # REST/WebSocket API
│   └── dashboard/          # Web UI
└── docs/
```

## Model Profiles

| Profile | Use Case | Recommended Model |
|---------|----------|-------------------|
| fast | Quick tasks, simple queries | llama3.2:3b (Ollama) |
| hq | Analysis, planning, architecture | claude-3-sonnet / gpt-4 |
| offline | Air-gapped environments | llama3.1:70b (Ollama) |

## On-Prem Deployment

### Mac Ultra Setup
```bash
# Install dependencies
brew install ollama docker docker-compose

# Start Ollama
ollama serve &
ollama pull llama3.2:3b
ollama pull llama3.1:70b

# Start Lantrn Agent Builder
cd /Volumes/NAS/lantrn-agent
./scripts/start.sh
```

### NAS Integration
- **Workspace Storage**: `/Volumes/NAS/lantrn-agent/workspace`
- **Model Cache**: `/Volumes/NAS/lantrn-agent/models`
- **Logs & Traces**: `/Volumes/NAS/lantrn-agent/logs`
- **Backups**: `/Volumes/NAS/lantrn-agent/backups`

## API Endpoints

```
POST /api/plan          # Start planning phase
GET  /api/plan/:id      # Get blueprint
POST /api/build/:id     # Execute blueprint
GET  /api/run/:id       # Get execution status
GET  /api/run/:id/trace # Get execution trace
POST /api/verify/:id    # Run verification
```

## Security Considerations

1. **Local-First**: All data stays on-prem
2. **Policy Enforcement**: Guardrails prevent unauthorized access
3. **Audit Trails**: All runs logged with full traces
4. **No Cloud Required**: Works with local Ollama models
5. **Optional VPN**: Secure remote access if needed
