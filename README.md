# Lantrn Agent Builder

On-premises deployable AI agent system combining **Agent Zero's** tool-based execution with **BMad v6 Alpha's** Plan → Build → Verify methodology.

## Features

- 🤖 **BMad Role Chain**: Analyst → PM → Architect → Dev → QA
- 📋 **Two-Phase Pipeline**: Plan → Build → Verify
- 🔧 **Tool Registry**: Code execution, file operations, browser automation
- 🏠 **On-Prem Ready**: Runs entirely on Mac Ultra + NAS
- 🦙 **Local LLM**: Ollama integration (llama3.2:3b, llama3.1:70b)
- 🔒 **Policy Guardrails**: File/network access control
- 📊 **Audit Trails**: Full traces of all agent runs

## Quick Start

### Prerequisites

- Python 3.11+
- Ollama (for local LLM)

### Installation

```bash
# Clone or navigate to the project
cd lantrn-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install Ollama models
ollama pull llama3.2:3b
ollama pull llama3.1:70b
```

### Initialize Workspace

```bash
# Initialize a new workspace
lantrn init

# This creates:
# - .bmad/profiles/    # Model profiles
# - .bmad/blueprints/  # Plan outputs
# - .bmad/runs/        # Execution manifests
# - agents/            # Agent definitions
# - policies/          # Security policies
```

### Usage

#### CLI

```bash
# Run the Plan phase
lantrn plan "Create a REST API for user management"

# Run the Build phase
lantrn build <blueprint_id>

# Run full pipeline
lantrn run "Create a REST API for user management"

# List available agents
lantrn agents

# List available models
lantrn models

# Start API server
lantrn serve
```

#### API

```bash
# Start the server
lantrn serve --port 8000

# API Endpoints
POST /api/plan          # Start planning phase
GET  /api/plan/:id      # Get blueprint
POST /api/build/:id     # Execute blueprint
GET  /api/run/:id       # Get execution status
GET  /api/run/:id/trace # Get execution trace
POST /api/run           # Run full pipeline

# WebSocket
WS /ws                  # Real-time updates
```

---

## Docker Deployment

### Overview

The Docker deployment is optimized for **Mac Ultra (ARM64)** with **NAS storage** integration. It includes:

- **lantrn-api**: Main API service
- **ollama**: Local LLM service
- **chromadb**: Vector database for memory
- **watchtower**: Optional auto-update service

### Prerequisites

- Docker Desktop for Mac (Apple Silicon)
- Minimum 16GB RAM (32GB+ recommended)
- 50GB+ free disk space for models
- Optional: NAS mounted at `/Volumes/NAS`

### Quick Start (Docker)

```bash
# Start all services
./scripts/start.sh

# Check status
docker compose ps

# View logs
docker compose logs -f lantrn-api

# Stop services
./scripts/stop.sh
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCKER NETWORK (lantrn-network)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ lantrn-api  │  │   ollama    │  │  chromadb   │             │
│  │   :8000     │──│   :11434    │  │   :8001     │             │
│  │             │  │             │  │             │             │
│  │ FastAPI     │  │ LLM Models  │  │ Vector DB   │             │
│  │ Playwright  │  │ llama3.2    │  │ Embeddings  │             │
│  │ ChromaDB    │  │ llama3.1    │  │             │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                    │
│         └────────────────┴────────────────┘                    │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────┐             │
│  │              DOCKER VOLUMES                    │             │
│  │  • lantrn-workspace (data, blueprints, runs)  │             │
│  │  • lantrn-ollama-models (LLM weights)         │             │
│  │  • lantrn-chromadb (vector embeddings)        │             │
│  └───────────────────────────────────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration

#### Environment Variables

Create a `.env` file in the project root:

```env
# Environment
ENV=production
LOG_LEVEL=INFO

# Model Configuration
DEFAULT_MODEL=llama3.2:3b
FAST_MODEL=llama3.2:3b
HQ_MODEL=llama3.1:70b

# API Security (change these!)
API_KEY=your-api-key-here
SECRET_KEY=your-secret-key-here

# NAS Paths (optional - uncomment and configure)
# NAS_PATH=/Volumes/NAS/lantrn
# OLLAMA_NAS_PATH=/Volumes/NAS/ollama/models
```

#### NAS Mount Configuration

For persistent storage on NAS, edit `docker-compose.yml`:

```yaml
services:
  lantrn-api:
    volumes:
      # Uncomment for NAS storage
      - /Volumes/NAS/lantrn/data:/app/workspace/data
      - /Volumes/NAS/lantrn/logs:/app/workspace/logs
      
  ollama:
    volumes:
      # Store models on NAS (recommended - models are large)
      - /Volumes/NAS/ollama/models:/root/.ollama
```

### Docker Commands

```bash
# Build the image
docker compose build

# Start services in background
docker compose up -d

# Start specific services
docker compose up -d lantrn-api chromadb

# View logs
docker compose logs -f

docker compose logs -f lantrn-api

# Check service status
docker compose ps

# Restart services
docker compose restart

# Stop services
docker compose down

# Stop and remove volumes (WARNING: deletes all data)
docker compose down -v

# Execute command in container
docker compose exec lantrn-api bash

# Pull new models
docker compose exec ollama ollama pull llama3.1:70b
```

### Health Checks

All services include health checks:

```bash
# Check API health
curl http://localhost:8000/

# Check Ollama health
curl http://localhost:11434/api/tags

# Check ChromaDB health
curl http://localhost:8001/api/v1/heartbeat
```

### Resource Limits

Default resource limits in `docker-compose.yml`:

| Service | Memory Limit | Memory Reserved |
|---------|-------------|-----------------|
| lantrn-api | 4GB | 2GB |
| ollama | 64GB | 16GB |
| chromadb | 2GB | 512MB |

Adjust based on your Mac Ultra configuration.

### Using Local Ollama

If you have Ollama running locally on your Mac:

```bash
# Start Ollama locally
ollama serve

# Pull models
ollama pull llama3.2:3b
ollama pull llama3.1:70b

# Start only API and ChromaDB (skip Ollama container)
docker compose up -d lantrn-api chromadb
```

The API will automatically detect and use the local Ollama instance.

### Troubleshooting

#### Common Issues

**1. Port Already in Use**
```bash
# Check what's using the port
lsof -i :8000
lsof -i :11434

# Stop conflicting services
./scripts/stop.sh
```

**2. Ollama Models Not Loading**
```bash
# Check Ollama logs
docker compose logs ollama

# Manually pull models
docker compose exec ollama ollama pull llama3.2:3b
```

**3. ChromaDB Connection Issues**
```bash
# Restart ChromaDB
docker compose restart chromadb

# Check ChromaDB logs
docker compose logs chromadb
```

**4. Playwright Browser Issues**
```bash
# Reinstall Playwright browsers
docker compose exec lantrn-api playwright install chromium --with-deps
```

**5. Memory Issues**
```bash
# Increase Docker memory limit in Docker Desktop
# Settings > Resources > Memory (recommend 32GB+ for Mac Ultra)
```

#### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f lantrn-api
docker compose logs -f ollama
docker compose logs -f chromadb

# Last 100 lines
docker compose logs --tail=100 lantrn-api
```

### Production Deployment

#### Security Recommendations

1. **Set API Keys**: Update `.env` with secure keys
2. **Enable HTTPS**: Use a reverse proxy (nginx, Caddy)
3. **Network Isolation**: Use Docker networks
4. **Regular Updates**: Enable watchtower for auto-updates

#### Backup Strategy

```bash
# Backup volumes
docker run --rm -v lantrn-workspace:/data -v $(pwd)/backup:/backup \
  alpine tar czf /backup/workspace-backup.tar.gz /data

# Backup Ollama models
docker run --rm -v lantrn-ollama-models:/data -v $(pwd)/backup:/backup \
  alpine tar czf /backup/ollama-backup.tar.gz /data
```

#### Monitoring

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Volume usage
docker volume ls
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LANTRN AGENT BUILDER                         │
├─────────────────────────────────────────────────────────────────┤
│  CLI / Dashboard / API Gateway                                  │
├─────────────────────────────────────────────────────────────────┤
│                    ORCHESTRATION LAYER                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│  │ Analyst │ │   PM    │ │Architect│  → Blueprint              │
│  └─────────┘ └─────────┘ └─────────┘                           │
├─────────────────────────────────────────────────────────────────┤
│                    EXECUTION LAYER                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────────────────────────────┐   │
│  │   Dev   │ │   QA    │ │     Tool Registry               │   │
│  └─────────┘ └─────────┘ │  • Code Execution               │   │
│                          │  • File Operations               │   │
│                          │  • Browser Agent                 │   │
│                          └─────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐   │
│  │   Memory    │ │  Policies   │ │    Model Adapters       │   │
│  │  (SQLite +  │ │ (Guardrails)│ │  • Ollama (local)       │   │
│  │  ChromaDB)  │ │             │ │  • OpenAI               │   │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## BMad v6 Alpha Methodology

### Phase 1: PLAN
1. **Analyst** - Gathers requirements, analyzes context
2. **PM** - Creates tasks, defines acceptance criteria
3. **Architect** - Designs solution, produces Blueprint

### Phase 2: BUILD & VERIFY
1. **Dev** - Executes Blueprint, writes code
2. **QA** - Runs tests, validates acceptance criteria

## Configuration

### Model Profiles

Located in `.bmad/profiles/*.yaml`:

```yaml
# fast.yaml
provider: ollama
model: llama3.2:3b
ctx_length: 128000
temperature: 0.7
```

### Policies

Located in `policies/org.yaml`:

```yaml
file_access:
  default: deny
  allow:
    - workspace/**
    - /tmp/**
  deny:
    - ~/.ssh/**
    - **/.credentials

network_access:
  default: deny
  allow:
    - localhost:11434
  deny:
    - "*"
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lantrn_agent tests/

# Run specific test
pytest tests/test_pipeline.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## License

MIT
