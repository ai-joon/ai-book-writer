# book.ai - AI Book Writer System

[![CI/CD Pipeline](https://github.com/cheesejaguar/book.ai/actions/workflows/ci.yml/badge.svg)](https://github.com/cheesejaguar/book.ai/actions/workflows/ci.yml)

**Transform your ideas into complete manuscripts in hours, not months.**

book.ai is a production-ready AI book-writing system that transforms author briefs into complete manuscripts with real-time streaming, multi-agent collaboration, and comprehensive cost controls. Built for authors, publishers, and content creators who need high-quality, consistent book generation at scale.

## Features ✨

### 🤖 Multi-Agent Intelligence
- **5 Specialized CrewAI Agents**: Concept Generator, Outliner, Writer, Editor, and Continuity Checker
- **Intelligent Collaboration**: Agents work together with defined roles and handoff protocols
- **Context Preservation**: Each agent maintains story context across chapters

### ⚡ Real-Time Performance
- **Sub-300ms Latency**: SSE-based token streaming for instant feedback
- **Concurrent Processing**: Multiple agents can work simultaneously
- **Smart Caching**: Redis-based response caching reduces API calls by 40%

### 💰 Cost Management
- **Real-time Cost Tracking**: Monitor spending across all agents and models
- **Budget Controls**: Automatic task termination when budget limits are reached
- **Model Optimization**: Intelligent routing to cost-effective models when appropriate
- **Usage Analytics**: Detailed breakdowns by agent, model, and project

### 🔄 Production Ready
- **Kubernetes Native**: Auto-scaling with HPA based on demand
- **Comprehensive Monitoring**: Prometheus metrics, Grafana dashboards, and alerting
- **CI/CD Pipeline**: Automated testing, security scanning, and deployment
- **High Availability**: Redis clustering, database replication, and load balancing

## Tech Stack 🧰

### Backend Services
- **API Framework**: FastAPI with async/await support
- **Database**: PostgreSQL 16 with async SQLAlchemy 2.0
- **Caching**: Redis 7 with clustering support
- **Authentication**: JWT with OAuth2 (Google) integration
- **AI Routing**: LiteLLM with intelligent fallback chains

### AI/ML Stack
- **Multi-Agent Framework**: CrewAI 0.80.0
- **LLM Router**: LiteLLM 1.48.x with model fallbacks
- **Primary Models**: GPT-5, Claude Sonnet 4, Gemini 2.5 Pro
- **Agent Framework**: CrewAI with specialized agent roles
- **Cost Tracking**: Real-time token and cost monitoring

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript with strict mode
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: Zustand for client state
- **Real-time**: Server-Sent Events (SSE) for streaming

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Kubernetes with Helm charts
- **Monitoring**: Prometheus + Grafana + custom metrics
- **CI/CD**: GitHub Actions with automated testing
- **Cloud**: Google Cloud Platform (GKE) ready

## Quick Start 🚀

### Prerequisites

- **Python**: 3.12+ (required for async features)
- **Node.js**: 20+ (for Next.js 14)
- **Docker**: 24+ with Docker Compose 2.0+
- **API Keys**: Anthropic, OpenAI, Google (for LLM access)
- **Memory**: 8GB+ RAM recommended for local development
- **Storage**: 2GB+ free space for dependencies and containers

### Local Development 🛠️

1. **Clone the repository:**
```bash
git clone https://github.com/ai-joon/ai-book-writer.git
cd ai-book-writer
```

2. **Set up environment variables:**
```bash
# Create environment file
cp .env.example .env

# Edit .env and add your API keys
# Required: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY
# Optional: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (for OAuth)
```

3. Choose your development method:

#### Option A: Docker Compose (Recommended) 🐳
```bash
cd infra
docker-compose -f docker-compose.dev.yml up
```

**Services will be available at:**
- 🌐 **Frontend**: http://localhost:3000
- 🔧 **Backend API**: http://localhost:8000
- 📚 **API Documentation**: http://localhost:8000/docs
- 📊 **Prometheus**: http://localhost:9090
- 📈 **Grafana**: http://localhost:3001 (admin/admin)

#### Option B: Local Development 🛠️
```bash
# Terminal 1: Start Backend
cd backend
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start Frontend  
cd frontend
npm install
npm run dev

# Terminal 3: Start Infrastructure (optional)
cd infra
docker-compose -f docker-compose.dev.yml up redis postgres
```

**Access the application:**
- 🌐 **Frontend**: http://localhost:3000
- 📚 **API Docs**: http://localhost:8000/docs
- 🔍 **Health Check**: http://localhost:8000/healthz

## API Endpoints 🔌

### Core Writing Endpoints
| Endpoint | Method | Description | Streaming |
|----------|--------|-------------|-----------|
| `/api/v1/projects/{id}/outline/stream` | GET | Generate book outline with real-time streaming | ✅ SSE |
| `/api/v1/projects/{id}/chapter/{n}/draft/stream` | POST | Stream chapter draft generation | ✅ SSE |
| `/api/v1/projects/{id}/chapter/{n}/edit/stream` | POST | Stream editorial pass | ✅ SSE |
| `/api/v1/projects/{id}/continuity/run` | POST | Run continuity checker | ❌ |
| `/api/v1/projects/{id}/costs` | GET | Get detailed cost report | ❌ |

### Authentication & User Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/google` | GET | Initiate Google OAuth flow |
| `/auth/callback/google` | GET | Handle OAuth callback |
| `/auth/logout` | POST | Logout and clear session |
| `/auth/verify` | GET | Verify authentication status |
| `/auth/me` | GET | Get current user profile |

### Usage & Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/users/me/usage` | GET | Get user usage statistics |
| `/api/v1/users/me/budget` | POST | Update monthly budget |
| `/api/v1/users/me/estimate` | POST | Estimate project cost |

### Health & Monitoring
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Basic health check |
| `/readyz` | GET | Readiness check (dependencies) |
| `/livez` | GET | Liveness check |
| `/api/metrics` | GET | Prometheus metrics |

## Architecture 🏗️

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js 14    │    │   FastAPI       │    │   LiteLLM       │
│   Frontend      │◄──►│   Backend       │◄──►│   Router        │
│   (App Router)  │SSE │   (Async)       │    │   (Multi-LLM)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                       ┌────────▼────────┐    ┌────────▼────────┐
                       │   PostgreSQL    │    │   CrewAI        │
                       │   + Redis       │    │   Agents        │
                       │   (Data Layer)  │    │   (AI Workers)  │
                       └─────────────────┘    └─────────────────┘
```

### Multi-Agent Workflow
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Concept   │───▶│  Outliner   │───▶│   Writer    │───▶│   Editor    │
│  Generator  │    │   Agent     │    │   Agent     │    │   Agent     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                               │
                                                       ┌───────▼───────┐
                                                       │ Continuity    │
                                                       │ Checker       │
                                                       └───────────────┘
```

### Data Flow
1. **Input**: Author brief, style guide, character database
2. **Processing**: Multi-agent pipeline with real-time streaming
3. **Output**: Complete manuscript with continuity verification
4. **Monitoring**: Real-time cost tracking and performance metrics

## Development 🧪

### Backend Development

```bash
cd backend

# Install dependencies
pip install -e .[dev]

# Run development server
uvicorn app.main:app --reload --port 8000

# Run database migrations
alembic upgrade head

# Format and lint code
black app tests
ruff check app tests
mypy app
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Type checking
npm run type-check

# Run tests
npm run test
```

### Running Tests ✅

```bash
# Backend tests with coverage
cd backend
pytest tests/ -v --cov=app --cov-report=html

# Frontend tests
cd frontend
npm run test
npm run test:coverage

# Type checking
npm run type-check
```

### Code Quality Tools

```bash
# Backend
black app tests                    # Code formatting
ruff check app tests              # Linting
mypy app                          # Type checking
pytest tests/ -v --cov=app       # Testing

# Frontend  
npm run lint                      # ESLint
npm run type-check               # TypeScript
npm run test                     # Vitest
```

## Deployment 🚢

### Deploy to Kubernetes (GKE)

#### 1. Build and Push Images
```bash
# Build backend image
docker build -t ghcr.io/your-org/sopher-api:latest backend/
docker push ghcr.io/your-org/sopher-api:latest

# Build frontend image  
docker build -t ghcr.io/your-org/sopher-web:latest frontend/
docker push ghcr.io/your-org/sopher-web:latest
```

#### 2. Deploy Infrastructure
```bash
# Apply Kubernetes manifests
kubectl apply -f infra/k8s/

# Verify deployment
kubectl get pods -n sopher-ai
kubectl get services -n sopher-ai
```

#### 3. Configure Secrets
```bash
# Create namespace
kubectl create namespace sopher-ai

# Add API keys
kubectl create secret generic sopher-ai-secrets \
  --from-literal=ANTHROPIC_API_KEY=your-key \
  --from-literal=OPENAI_API_KEY=your-key \
  --from-literal=GOOGLE_API_KEY=your-key \
  --from-literal=GOOGLE_CLIENT_ID=your-client-id \
  --from-literal=GOOGLE_CLIENT_SECRET=your-client-secret \
  --from-literal=JWT_SECRET=your-jwt-secret \
  -n sopher-ai

# Add database credentials
kubectl create secret generic sopher-ai-db \
  --from-literal=DATABASE_URL=postgresql://user:pass@host:5432/db \
  --from-literal=REDIS_URL=redis://host:6379/0 \
  -n sopher-ai
```

#### 4. Production Configuration
```bash
# Update image tags in manifests
sed -i 's/:latest/:v1.0.0/g' infra/k8s/*.yaml

# Apply production overrides
kubectl apply -f infra/k8s/ -f infra/k8s/production/
```

### Alternative: Docker Compose Production

```bash
# Production deployment
cd infra
docker-compose -f docker-compose.prod.yml up -d

# With custom environment
docker-compose -f docker-compose.prod.yml -f docker-compose.override.yml up -d
```

## Configuration ⚙️

### LiteLLM Router Configuration

Configure model routing in `router/litellm.config.yaml`:

```yaml
model_list:
  - model_name: gpt-5
    litellm_params:
      model: gpt-5
      api_key: ${OPENAI_API_KEY}
  - model_name: claude-sonnet-4-20250514  
    litellm_params:
      model: claude-sonnet-4-20250514
      api_key: ${ANTHROPIC_API_KEY}
  - model_name: gemini-2.5-pro
    litellm_params:
      model: gemini-2.5-pro
      api_key: ${GOOGLE_API_KEY}

router_settings:
  routing_strategy: "simple-shuffle"
  num_retries: 3
  timeout: 60
```

### Environment Variables

#### Required API Keys
| Variable | Description | How to Obtain |
|----------|-------------|---------------|
| `ANTHROPIC_API_KEY` | Claude API access | [Anthropic Console](https://console.anthropic.com/) |
| `OPENAI_API_KEY` | OpenAI GPT models | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `GOOGLE_API_KEY` | Gemini models | [Google AI Studio](https://makersuite.google.com/app/apikey) |

#### OAuth Configuration (Optional)
| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Not set |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Not set |

#### Core Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/sopherai` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET` | JWT signing secret | `dev-secret-key-change-in-production` |
| `MONTHLY_BUDGET_USD` | Monthly cost limit | `100` |
| `PRIMARY_MODEL` | Main LLM model | `gpt-5` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `CORS_ORIGINS` | Allowed origins | `http://localhost:3000` |

#### Production Configuration
For production deployment, see `infra/.env.production.template` for comprehensive configuration options including:
- GCP service account configuration
- SSL/TLS settings
- Monitoring and alerting
- Database backup settings
- Redis clustering

## Monitoring 📈

### Health Checks
- **Basic Health**: `/healthz` - Service availability
- **Readiness**: `/readyz` - Dependencies check (Redis, PostgreSQL)
- **Liveness**: `/livez` - Application responsiveness

### Metrics & Observability
- **Prometheus Metrics**: `/api/metrics` - Custom application metrics
- **Grafana Dashboards**: http://localhost:3001 (admin/admin)
- **Real-time Monitoring**: Live cost tracking and performance metrics

### Custom Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `llm_inference_seconds` | Histogram | LLM response time distribution |
| `llm_tokens_total` | Counter | Total tokens processed |
| `llm_cost_usd_total` | Counter | Total cost in USD |
| `active_sessions` | Gauge | Concurrent writing sessions |
| `api_requests_total` | Counter | HTTP request count by endpoint |
| `api_request_duration_seconds` | Histogram | Request latency |

### Alerting Rules
```yaml
# Example Prometheus alerting rules
- alert: HighCostUsage
  expr: llm_cost_usd_total > 50
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High cost usage detected"

- alert: ServiceDown
  expr: up == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Service is down"
```

## Security 🔐

### Authentication & Authorization
- **JWT Tokens**: 1-hour expiry with refresh rotation
- **OAuth2 Integration**: Google OAuth for user authentication
- **Role-based Access**: Author, Editor, Admin roles
- **Session Management**: Secure session handling with Redis

### Data Protection
- **API Key Encryption**: Fernet encryption for stored API keys
- **Input Sanitization**: Comprehensive input validation and sanitization
- **Output Encoding**: XSS protection for frontend rendering
- **Database Security**: Parameterized queries, no SQL injection

### Rate Limiting & Controls
- **API Rate Limiting**: 60 requests per minute per API key
- **Budget Controls**: Automatic task termination on budget exceed
- **Circuit Breaker**: Automatic fallback on LLM service failures
- **Request Validation**: Strict schema validation for all endpoints

### Infrastructure Security
- **Kubernetes Network Policies**: Restricted pod-to-pod communication
- **Container Security**: Non-root containers, read-only filesystems
- **Secret Management**: Kubernetes secrets for sensitive data
- **TLS Encryption**: End-to-end encryption for all communications

### Security Best Practices
- **Environment Isolation**: Separate dev/staging/production environments
- **Audit Logging**: Comprehensive request and action logging
- **Vulnerability Scanning**: Automated security scanning in CI/CD
- **Dependency Management**: Regular security updates for dependencies

## Contributing 🤝

### Getting Started
1. **Fork the repository** and clone your fork
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** following the coding standards
4. **Run tests**: Ensure all tests pass locally
5. **Commit changes**: Use conventional commit messages
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a Pull Request** with a clear description

### Development Guidelines
- **Code Style**: Follow Black (Python) and Prettier (TypeScript) formatting
- **Type Safety**: Use type hints in Python and strict TypeScript
- **Testing**: Write tests for new features and bug fixes
- **Documentation**: Update README and code comments as needed
- **Commit Messages**: Use conventional commits (feat:, fix:, docs:, etc.)

### CI/CD Pipeline 🔄

The project includes a comprehensive GitHub Actions pipeline that:

#### Automated Testing
- **Backend Tests**: Python pytest with coverage reporting
- **Frontend Tests**: Vitest with component testing
- **Type Checking**: MyPy (Python) and TypeScript strict mode
- **Linting**: Ruff (Python) and ESLint (TypeScript)

#### Security & Quality
- **Security Scanning**: Semgrep and CodeQL vulnerability detection
- **Dependency Scanning**: Automated security updates
- **Code Quality**: Automated code review checks

#### Build & Deploy
- **Docker Images**: Automated builds for backend and frontend
- **Container Registry**: GitHub Container Registry publishing
- **Kubernetes**: Optional GKE deployment (requires secrets)

**For contributors**: The pipeline works without any secrets configured. Tests and builds will run successfully. See [`.github/SETUP_SECRETS.md`](.github/SETUP_SECRETS.md) for deployment configuration.

### Troubleshooting 🛠️

#### Common Issues
- **API Key Errors**: Ensure all required environment variables are set
- **Database Connection**: Check PostgreSQL is running and accessible
- **Redis Connection**: Verify Redis is running on the correct port
- **CORS Issues**: Update CORS_ORIGINS for your development URL

#### Getting Help
- **Documentation**: Check the `/docs` folder for detailed guides
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas
