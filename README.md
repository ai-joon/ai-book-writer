# sopher.ai

Production-ready AI book-writing system that transforms author briefs into complete manuscripts with real-time streaming, multi-agent collaboration, and comprehensive cost controls.

## Features

- **Real-time Streaming**: SSE-based token streaming with sub-300ms latency
- **Multi-Agent System**: 5 specialized CrewAI agents (Concept, Outline, Writer, Editor, Continuity)
- **Intelligent Routing**: LiteLLM router with primary/fallback models and overflow handling
- **Cost Management**: Real-time cost tracking with budget controls and agent allocation
- **Continuity Checking**: Automated consistency verification across chapters
- **Production Ready**: Dockerized, Kubernetes-ready with HPA, monitoring, and CI/CD

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL, Redis
- **AI/ML**: LiteLLM, CrewAI, Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Zustand
- **Infrastructure**: Docker, Kubernetes (GKE), Prometheus, Grafana
- **CI/CD**: GitHub Actions, automated testing, security scanning

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- API Keys: Anthropic, OpenAI, Google (for LLMs)

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/cheesejaguar/sopher.ai.git
cd sopher.ai
```

2. Set up environment variables:
```bash
cp .env.example .env
# Add your API keys to .env
```

3. Start services with Docker Compose:
```bash
cd infra
docker-compose -f docker-compose.dev.yml up
```

4. Access the application:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/projects/{id}/outline/stream` | POST | Generate book outline with SSE streaming |
| `/api/v1/projects/{id}/chapter/{n}/draft/stream` | POST | Stream chapter draft generation |
| `/api/v1/projects/{id}/chapter/{n}/edit/stream` | POST | Stream editorial pass |
| `/api/v1/projects/{id}/continuity/run` | POST | Run continuity checker |
| `/api/v1/projects/{id}/costs` | GET | Get cost report |
| `/ws/agents/{id}` | WebSocket | Real-time agent status updates |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI    │────▶│   LiteLLM   │
│   Frontend  │ SSE │   Backend    │     │   Router    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                     │
                    ┌──────▼──────┐      ┌──────▼──────┐
                    │ PostgreSQL  │      │   CrewAI    │
                    │   + Redis   │      │   Agents    │
                    └─────────────┘      └─────────────┘
```

## Development

### Backend Development

```bash
cd backend
pip install -e .[dev]
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm run test
npm run type-check
```

## Deployment

### Deploy to Kubernetes (GKE)

1. Build and push images:
```bash
docker build -t ghcr.io/your-org/sopher-api:latest backend/
docker build -t ghcr.io/your-org/sopher-web:latest frontend/
docker push ghcr.io/your-org/sopher-api:latest
docker push ghcr.io/your-org/sopher-web:latest
```

2. Apply Kubernetes manifests:
```bash
kubectl apply -f infra/k8s/
```

3. Configure secrets:
```bash
kubectl create secret generic sopher-ai-secrets \
  --from-literal=ANTHROPIC_API_KEY=your-key \
  --from-literal=OPENAI_API_KEY=your-key \
  --from-literal=GOOGLE_API_KEY=your-key \
  -n sopher-ai
```

## Configuration

### LiteLLM Router

Configure model routing in `router/litellm.config.yaml`:
- Primary: Claude 3.5 Sonnet
- Secondary: GPT-4o
- Overflow: Gemini 1.5 Pro
- Budget allocation by agent

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GOOGLE_API_KEY` | Google API key | - |
| `JWT_SECRET` | JWT signing secret | - |
| `MONTHLY_BUDGET_USD` | Monthly cost limit | 500 |

## Monitoring

- **Metrics**: Prometheus metrics at `/api/metrics`
- **Health Checks**: `/healthz`, `/readyz`, `/livez`
- **Custom Metrics**:
  - `llm_inference_seconds`: LLM response time
  - `llm_tokens_total`: Token usage
  - `llm_cost_usd_total`: Cost tracking
  - `active_sessions`: Concurrent writing sessions

## Security

- JWT authentication with 1-hour expiry
- API key encryption with Fernet
- Rate limiting (60 RPM per key)
- Input sanitization and output encoding
- Circuit breaker for LLM calls
- Kubernetes network policies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file