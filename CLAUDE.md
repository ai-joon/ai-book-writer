# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sopher.ai is a production-ready AI book-writing system that transforms author briefs into complete manuscripts. The system uses real-time streaming, multi-agent collaboration via CrewAI, and comprehensive cost controls. Built as a microservices architecture with FastAPI backend, Next.js frontend, and deployed on Kubernetes.

## Architecture Overview

The system follows a three-tier architecture:

1. **Frontend**: Next.js 14 with App Router, Zustand state management, real-time SSE streaming
2. **Backend**: FastAPI with async SQLAlchemy, Redis caching, LiteLLM routing, CrewAI agents
3. **Infrastructure**: PostgreSQL, Redis, Prometheus monitoring, Kubernetes deployment

### Key Components

- **CrewAI Multi-Agent System**: 5 specialized agents (ConceptGenerator, Outliner, Writer, Editor, ContinuityChecker)
- **LiteLLM Router**: Primary/secondary/overflow model routing (gpt-5 → claude-sonnet-4-20250514 → gemini-2.5-pro)
- **SSE Streaming**: Real-time token streaming with < 300ms latency via Server-Sent Events
- **Cost Tracking**: Real-time cost monitoring with budget controls and per-agent allocation
- **Caching**: Redis-based response caching and rate limiting

## Development Commands

### Backend Development

```bash
cd backend
pip install -e .[dev]                    # Install with dev dependencies
uvicorn app.main:app --reload            # Run development server (port 8000)
pytest tests/ -v --cov=app              # Run tests with coverage
pytest tests/test_api_contract.py::test_health_endpoint  # Run single test
black app tests                          # Format code
ruff check app tests                     # Lint code  
mypy app                                 # Type check
```

### Frontend Development

```bash
cd frontend
npm install                              # Install dependencies
npm run dev                              # Run development server (port 3000)
npm run build                            # Build for production
npm run lint                             # Lint code (ESLint with Next.js rules)
npm run type-check                       # TypeScript strict mode checking
npm run test                             # Run color contrast tests
```

### Quality Assurance Commands

```bash
# Backend: Run all quality checks
cd backend && black app tests && ruff check app tests && mypy app && pytest tests/ -v

# Frontend: Run all quality checks  
cd frontend && npm run lint && npm run type-check && npm run build

# Full stack verification
cd backend && pytest tests/ -v && cd ../frontend && npm run type-check
```

### Docker Development

```bash
cd infra
docker-compose -f docker-compose.dev.yml up        # Start all services
docker-compose -f docker-compose.dev.yml up -d     # Start in background
docker-compose -f docker-compose.dev.yml logs -f   # Follow logs
docker-compose -f docker-compose.dev.yml down      # Stop all services
```

## Database Architecture

The system uses 5 main tables (defined in `backend/app/models.py`) with UUID primary keys:

- **projects**: Book projects with JSONB settings
- **sessions**: Writing sessions linked to projects  
- **events**: Action logs with JSONB payloads
- **artifacts**: Generated content (outlines, chapters) with optional blob storage
- **costs**: Token usage and cost tracking per agent/session

Database migrations are handled through SQLAlchemy with async support. All operations use proper indexing on (session_id, created_at) for performance.

## Agent System

The CrewAI agents (in `backend/app/agents/agents.py`) work in a coordinated pipeline:

1. **ConceptGenerator**: Expands brief into rich concepts
2. **Outliner**: Creates detailed chapter-by-chapter structure  
3. **Writer**: Generates chapter content following style guides
4. **Editor**: Performs structural editing and improvements
5. **ContinuityChecker**: Validates consistency across characters/timeline

Agents can work in parallel for chapter generation and use shared context through Redis caching.

## API Design Patterns

### Main Endpoints
- `/api/v1/projects/{id}/outline/stream` - Generate book outline with SSE streaming
- `/api/v1/projects/{id}/chapter/{n}/draft/stream` - Stream chapter draft generation
- `/api/v1/projects/{id}/chapter/{n}/edit/stream` - Stream editorial pass
- `/api/v1/projects/{id}/continuity/run` - Run continuity checker
- `/api/v1/projects/{id}/costs` - Get cost report
- `/ws/agents/{id}` - WebSocket for real-time agent status updates

### SSE Streaming Pattern
All streaming endpoints follow this pattern:
- Token events: `{"event": "token", "data": "content"}`
- Checkpoints: `{"event": "checkpoint", "data": "{\"progress\": 0.5}"}`
- Completion: `{"event": "complete", "data": "{\"tokens\": 1000}"}`

Authentication uses JWT with 1-hour expiry. Rate limiting is per-key (60 RPM). All costs are tracked in real-time with budget controls.

## Environment Configuration

Required environment variables:
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`: LLM provider keys
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql+asyncpg://postgres:postgres@localhost:5432/sopherai`)
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379/0`)
- `JWT_SECRET`: JWT signing secret (generate with `openssl rand -hex 32`)
- `MONTHLY_BUDGET_USD`: Cost limit (default: 100)
- `PRIMARY_MODEL`: Main LLM model (default: gpt-5)

See `.env.example` for complete configuration with descriptions.

## Development Setup

### Quick Start with .env.example

1. **Copy the template**: `cp .env.example .env`
2. **Add your API keys** (required):
   - `ANTHROPIC_API_KEY`: Get from [Anthropic Console](https://console.anthropic.com/)
   - `OPENAI_API_KEY`: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
   - `GOOGLE_API_KEY`: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
3. **Adjust configuration** if needed (optional):
   - Database URL if not using localhost PostgreSQL
   - Redis URL if not using localhost Redis
   - Log level for debugging (`LOG_LEVEL=DEBUG`)
4. **Generate secure secrets for production**:
   - JWT_SECRET: `openssl rand -hex 32`
   - FERNET_KEY: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### Development Workflow Options

#### Docker Compose (Recommended)
```bash
cd infra
docker-compose -f docker-compose.dev.yml up
```
- Automatically sets up PostgreSQL, Redis, and all services
- Hot reload enabled for both frontend and backend
- Access at http://localhost:3000 (frontend), http://localhost:8000 (backend API)
- API docs at http://localhost:8000/docs

#### Local Development
```bash
# Backend
cd backend
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```
- Requires local PostgreSQL and Redis installation
- More control over individual services
- Better for debugging specific components

### GitHub Actions Configuration

For contributors: The CI/CD pipeline runs tests and builds without requiring any secrets. Deployment steps are optional and only run for the main repository with proper GCP credentials configured.

See `.github/SETUP_SECRETS.md` for setting up your own deployment pipeline.

## Key File Locations

### Frontend
- `frontend/lib/zustand.ts`: Global state store with TypeScript interfaces (Message, Chapter, Project, AppState)
- `frontend/app/`: Next.js App Router pages and components
- `frontend/components/ui/`: Reusable UI components (Radix UI based)
- Uses `@/*` path alias for imports (configured in tsconfig.json)

### Backend
- `backend/app/agents/agents.py`: BookWritingAgents class with 5 specialized CrewAI agents
- `backend/app/models.py`: SQLAlchemy database models
- `backend/app/schemas.py`: Pydantic validation schemas
- `backend/app/routers/`: API endpoint implementations
- `backend/app/main.py`: FastAPI application entry point

### Configuration
- `router/litellm.config.yaml`: LiteLLM router configuration with model fallbacks and budget allocation
- `.env.example`: Environment variable template
- `infra/docker-compose.dev.yml`: Docker Compose configuration for local development
- `infra/k8s/`: Kubernetes deployment manifests

## Testing Strategy

### Backend Testing
- Test files: `backend/tests/test_api_contract.py`, `backend/tests/test_properties.py`
- Run with: `pytest tests/ -v --cov=app`
- Currently 13/15 tests passing (2 skipped due to complex SQLAlchemy mocking)
- Property-based testing with Hypothesis for schema validation

### Frontend Testing
- Color contrast test: `frontend/tests/color-contrast.test.js`
- Run with: `npm run test`
- TypeScript strict mode and ESLint for quality assurance
- No comprehensive test suite yet

### Code Quality Tools
- **Backend**: Black (100 char line length), Ruff (E,F,I,N,W rules), MyPy (strict)
- **Frontend**: ESLint (Next.js core-web-vitals), TypeScript strict mode

## Deployment Notes

The system is containerized and Kubernetes-ready:
- HPA scales 2-10 pods based on CPU/memory/active_sessions
- Health checks on `/healthz`, `/readyz`, `/livez`
- Prometheus metrics at `/api/metrics`
- Rolling deployments with zero downtime

When modifying streaming endpoints, ensure proper cleanup of SSE connections and background tasks to prevent memory leaks.

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) includes:
- **Security Scanning**: CodeQL analysis for Python and JavaScript-TypeScript
- **Quality Gates**: Backend linting (ruff, black, mypy), frontend linting (ESLint, TypeScript)
- **Testing**: Automated test execution with PostgreSQL and Redis services
- **Docker**: Image building and pushing to GitHub Container Registry
- **Deployment**: Optional GKE deployment (requires secrets configuration)

## Common Issues and Solutions

- **TypeScript Path Resolution**: Remove explicit `baseUrl` from tsconfig.json - Next.js 14 App Router handles path resolution internally
- **Ruff Line Length**: Use multi-line string formatting for long pytest.mark.skip decorators
- **Database Connection**: Ensure PostgreSQL is running and `DATABASE_URL` is correctly set
- **Redis Connection**: Ensure Redis is running and `REDIS_URL` is correctly set
- **API Keys**: All three LLM provider keys (Anthropic, OpenAI, Google) are required for full functionality
- **CORS Issues**: Check `CORS_ORIGINS` environment variable includes your frontend URL
- Remember to always ensure all unit tests are passing, and lint is clean