# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sopher.ai is a production-ready AI book-writing system that transforms author briefs into complete manuscripts. The system uses real-time streaming, multi-agent collaboration via CrewAI, and comprehensive cost controls. It's built as a microservices architecture with FastAPI backend, Next.js frontend, and deployed on Kubernetes.

## Architecture Overview

The system follows a three-tier architecture:

1. **Frontend**: Next.js 14 with App Router, Zustand state management, real-time SSE streaming
2. **Backend**: FastAPI with async SQLAlchemy, Redis caching, LiteLLM routing, CrewAI agents
3. **Infrastructure**: PostgreSQL, Redis, Prometheus monitoring, Kubernetes deployment

### Key Components

- **CrewAI Multi-Agent System**: 5 specialized agents (ConceptGenerator, Outliner, Writer, Editor, ContinuityChecker)
- **LiteLLM Router**: Primary/secondary/overflow model routing (Claude 3.5 Sonnet → GPT-4o → Gemini 1.5 Pro)
- **SSE Streaming**: Real-time token streaming with < 300ms latency via Server-Sent Events
- **Cost Tracking**: Real-time cost monitoring with budget controls and per-agent allocation
- **Caching**: Redis-based response caching and rate limiting

## Development Commands

### Backend Development

```bash
cd backend
pip install -e .[dev]                    # Install with dev dependencies
uvicorn app.main:app --reload            # Run development server
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
npm run dev                              # Run development server
npm run build                            # Build for production
npm run lint                             # Lint code (ESLint with Next.js rules)
npm run type-check                       # TypeScript strict mode checking
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
```

## Database Architecture

The system uses 5 main tables with UUID primary keys:

- **projects**: Book projects with JSONB settings
- **sessions**: Writing sessions linked to projects  
- **events**: Action logs with JSONB payloads
- **artifacts**: Generated content (outlines, chapters) with optional blob storage
- **costs**: Token usage and cost tracking per agent/session

Database migrations are handled through SQLAlchemy with async support. All operations use proper indexing on (session_id, created_at) for performance.

## Agent System

The CrewAI agents work in a coordinated pipeline:

1. **ConceptGenerator**: Expands brief into rich concepts
2. **Outliner**: Creates detailed chapter-by-chapter structure  
3. **Writer**: Generates chapter content following style guides
4. **Editor**: Performs structural editing and improvements
5. **ContinuityChecker**: Validates consistency across characters/timeline

Agents can work in parallel for chapter generation and use shared context through Redis caching.

## API Design Patterns

All streaming endpoints follow SSE pattern:
- Token events: `{"event": "token", "data": "content"}`
- Checkpoints: `{"event": "checkpoint", "data": "{\"progress\": 0.5}"}`
- Completion: `{"event": "complete", "data": "{\"tokens\": 1000}"}`

Authentication uses JWT with 1-hour expiry. Rate limiting is per-key (60 RPM). All costs are tracked in real-time with budget controls.

## Environment Configuration

Required environment variables:
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`: LLM provider keys
- `DATABASE_URL`: PostgreSQL connection string  
- `REDIS_URL`: Redis connection string
- `JWT_SECRET`: JWT signing secret
- `MONTHLY_BUDGET_USD`: Cost limit (default: 500)

## Important File Structure Notes

### Frontend State Management
- `frontend/lib/zustand.ts`: Global state store with TypeScript interfaces (Message, Chapter, Project, AppState)
- Uses persistence middleware for auth tokens and project data
- Import with: `import { useStore } from '@/lib/zustand'` (path alias configured in tsconfig.json)

### Backend Agent System
- `backend/app/agents/agents.py`: BookWritingAgents class with 5 specialized CrewAI agents
- Each agent has specific role, goal, and backstory for optimal performance
- Async methods: `generate_concepts()`, `create_outline()`, `write_chapter()`, `edit_chapter()`, `check_continuity()`

### Database Schema
- All tables use UUID primary keys with postgresql JSONB for metadata storage
- Indexed on (session_id, created_at) for performance
- SQLAlchemy async models with proper relationships and cascading deletes

## Testing Strategy

- **Unit Tests**: Mock LLM responses, validate schemas and business logic
- **Property Tests**: Use Hypothesis for schema validation and edge cases
- **API Tests**: Contract testing with mocked authentication (13/15 tests currently passing)
- **Coverage**: Target 90% excluding raw LLM content

### Known Test Status
- `test_outline_stream_contract` and `test_cost_tracking` are skipped due to complex SQLAlchemy model mocking
- All health endpoints, validation, rate limiting, and schema tests pass
- Frontend has no test suite yet - uses TypeScript strict mode and ESLint for quality assurance

### Code Quality Tools Configuration
- **Backend**: Black (100 char line length), Ruff (E,F,I,N,W rules), MyPy (strict)
- **Frontend**: ESLint (Next.js core-web-vitals), TypeScript strict mode, no explicit Prettier
- **Path mapping**: Frontend uses `@/*` alias for imports (configured in tsconfig.json)

## Deployment Notes

The system is containerized and Kubernetes-ready:
- HPA scales 2-10 pods based on CPU/memory/active_sessions
- Health checks on `/healthz`, `/readyz`, `/livez`
- Prometheus metrics at `/api/metrics`
- Rolling deployments with zero downtime

When modifying streaming endpoints, ensure proper cleanup of SSE connections and background tasks to prevent memory leaks.

## CI/CD Configuration

GitHub Actions workflow (`.github/workflows/ci.yml`) includes:
- **Security Scanning**: CodeQL analysis with matrix strategy for Python and JavaScript-TypeScript
- **Quality Gates**: Backend linting (ruff, black, mypy), frontend linting (ESLint, TypeScript)
- **Testing**: Automated test execution with proper dependency installation
- **Docker**: Automated image building and security scanning

### Common Issues and Solutions
- **TypeScript Path Resolution**: Remove explicit `baseUrl` from tsconfig.json - Next.js 14 App Router handles path resolution internally
- **Ruff Line Length**: Use multi-line string formatting for long pytest.mark.skip decorators
- **CodeQL**: Ensure proper init/autobuild/analyze sequence with correct language parameters