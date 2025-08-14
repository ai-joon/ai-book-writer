# Sopher.AI Infrastructure Deployment

This directory contains Docker Compose configurations and supporting files for deploying Sopher.AI to various environments, optimized for Google Kubernetes Engine (GKE).

## Quick Start

1. **Copy environment template:**
   ```bash
   cd infra
   cp .env.production.template .env.production
   # Edit .env.production with your actual values
   ```

2. **Start the application:**
   ```bash
   # Development (uses docker-compose.dev.yml + docker-compose.override.yml)
   docker-compose -f docker-compose.dev.yml up -d
   
   # Production
   docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
   
   # Staging
   docker-compose -f docker-compose.prod.yml -f docker-compose.staging.yml --env-file .env.staging up -d
   ```

## Architecture

The deployment includes:

- **FastAPI Backend** (Port 8000): Main application API with metrics on port 9000
- **Next.js Frontend** (Port 3000): Web application interface
- **PostgreSQL** (Port 5432): Primary database
- **Redis** (Port 6379): Caching and session storage
- **Prometheus** (Port 9090): Metrics collection
- **Grafana** (Port 3001): Monitoring dashboard
- **Nginx** (Port 80/443): Reverse proxy and load balancer

## Environment Configurations

### Development (`docker-compose.dev.yml` + `docker-compose.override.yml`)
- Hot reload enabled
- Debug logging
- Exposed database ports
- Development secrets

### Production (`docker-compose.prod.yml`)
- Multi-replica deployment
- Resource limits and health checks
- Production security settings
- Comprehensive monitoring

### Staging (`docker-compose.staging.yml`)
- Production-like with reduced resources
- Debug logging enabled
- Separate database namespace

## Security Features

- **Non-root containers**: All services run as non-root users
- **Read-only filesystems**: Containers use read-only root filesystems where possible
- **Security options**: `no-new-privileges` enabled
- **Network isolation**: Services separated into logical networks
- **Secret management**: Environment-based configuration
- **Rate limiting**: API and authentication endpoints protected

## Performance Optimizations

- **Resource limits**: CPU and memory constraints for efficient scheduling
- **Health checks**: Proper startup, readiness, and liveness probes
- **Connection pooling**: Optimized database and Redis connections
- **Caching**: Multi-layer caching with Redis and HTTP caches
- **Compression**: Gzip compression for web assets

## Monitoring and Observability

- **Prometheus metrics**: Application and infrastructure metrics
- **Grafana dashboards**: Pre-configured monitoring dashboards
- **Health endpoints**: `/healthz`, `/readyz`, `/livez` for Kubernetes
- **Structured logging**: JSON logs with proper levels
- **Alerting**: Comprehensive alert rules for critical issues

## Directory Structure

```
infra/
├── docker-compose.dev.yml         # Development configuration
├── docker-compose.prod.yml        # Production configuration  
├── docker-compose.override.yml    # Development overrides
├── docker-compose.staging.yml     # Staging overrides
├── .env.production.template       # Environment template
├── monitoring/
│   ├── prometheus.yml            # Prometheus configuration
│   └── alerts.yml               # Alert rules
├── redis/
│   └── redis.conf               # Redis configuration
├── postgres/
│   ├── postgresql.conf          # PostgreSQL configuration
│   └── pg_hba.conf             # Authentication configuration
└── nginx/
    ├── nginx.conf              # Main Nginx configuration
    └── conf.d/
        └── sopher-ai.conf      # Application-specific configuration
```

## Environment Variables

Key environment variables (see `.env.production.template` for complete list):

```bash
# Database
POSTGRES_PASSWORD=secure_password
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# LLM APIs
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Security
JWT_SECRET=secure_jwt_secret
GRAFANA_ADMIN_PASSWORD=secure_admin_password

# Application
MONTHLY_BUDGET_USD=500
CORS_ORIGINS=https://sopher.ai,https://www.sopher.ai
```

## Deployment Commands

### Local Development
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

### Production Deployment
```bash
# Build and start
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Scale services
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --scale backend=5 --scale frontend=3

# Rolling update
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps backend
```

### Health Checks
```bash
# Check service health
curl http://localhost:8000/healthz  # Backend health
curl http://localhost:3000/         # Frontend health
curl http://localhost:9090/-/healthy # Prometheus health

# Check metrics
curl http://localhost:8000/api/metrics  # Application metrics
curl http://localhost:9090/metrics      # Prometheus metrics
```

## GKE Migration Notes

This Docker Compose setup is designed to translate well to Kubernetes:

1. **Resource Limits**: Already configured for HPA compatibility
2. **Health Checks**: Standard Kubernetes probe format
3. **Configuration**: Environment-based, easily converted to ConfigMaps/Secrets
4. **Networks**: Will map to Kubernetes Services
5. **Volumes**: Use persistent volumes or GCP storage classes

### Converting to Kubernetes

The existing `k8s/` directory contains Kubernetes manifests that correspond to this Docker Compose setup. Key conversions:

- Docker Compose services → Kubernetes Deployments
- Docker networks → Kubernetes Services
- Docker volumes → PersistentVolumeClaims
- Environment variables → ConfigMaps/Secrets

## Troubleshooting

### Common Issues

1. **Container fails to start**:
   ```bash
   docker-compose logs service_name
   ```

2. **Database connection issues**:
   - Check PostgreSQL health: `docker-compose exec postgres pg_isready`
   - Verify credentials in environment file
   - Check network connectivity between services

3. **Redis connection issues**:
   - Test Redis: `docker-compose exec redis redis-cli ping`
   - Verify Redis configuration and memory limits

4. **High memory usage**:
   - Monitor with: `docker stats`
   - Adjust resource limits in compose files
   - Check for memory leaks in application logs

5. **Performance issues**:
   - Check Prometheus metrics at `http://localhost:9090`
   - Review Grafana dashboards at `http://localhost:3001`
   - Monitor container resource usage

### Debugging Commands

```bash
# Container shell access
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose exec postgres psql -U postgres

# Resource usage
docker stats

# Service logs
docker-compose logs -f --tail=100 backend
docker-compose logs -f --tail=100 frontend

# Network inspection
docker network ls
docker network inspect infra_frontend
```

## Security Considerations

1. **Secrets Management**: Never commit `.env` files with real secrets
2. **Network Isolation**: Services communicate through defined networks only
3. **User Permissions**: All containers run as non-root users
4. **File Permissions**: Read-only filesystems where possible
5. **Monitoring**: Enable audit logging and alerting for security events

## Performance Tuning

1. **Database**: Adjust PostgreSQL settings in `postgres/postgresql.conf`
2. **Caching**: Tune Redis configuration in `redis/redis.conf`
3. **Web Server**: Optimize Nginx settings in `nginx/nginx.conf`
4. **Application**: Monitor metrics and adjust resource limits
5. **Scaling**: Use Docker Compose scaling or migrate to Kubernetes HPA

For more detailed information, see the main project documentation in the root `CLAUDE.md` file.