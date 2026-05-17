# Docker Setup Guide

This project is fully containerized with Docker to ensure isolation and reproducibility.

## 🏗️ Architecture

The system is composed of 3 core containers:

1. **qdrant** - Vector database (official image)
2. **api** - FastAPI backend (port 8000), exposes `/metrics` for Prometheus
3. **streamlit** - Streamlit frontend (port 8501)

All containers communicate through the private Docker network `rag-network`.

An optional **monitoring** overlay adds Prometheus (9090) and Grafana (3000); see [Monitoring stack](#-monitoring-stack-optional).

## 🚀 Quick Start

### 1. Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and add your `OPENAI_API_KEY`.

### 2. Start

```bash
# Build and start all services
make docker-up-build

# Or manually
docker-compose up -d --build
```

### 3. Access

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Streamlit**: http://localhost:8501
- **Qdrant**: http://localhost:6333/dashboard

### 4. Logs

```bash
# All services
make docker-logs

# API only
make docker-logs-api

# Streamlit only
make docker-logs-streamlit
```

## 🛠️ Useful commands

```bash
# Build images
make docker-build

# Start services
make docker-up

# Stop services
make docker-down

# Restart services
make docker-down && make docker-up

# Clean everything (containers, volumes, images)
make docker-clean

# Development mode (with hot reload)
make docker-dev

# Open shell in containers
make docker-shell-api
make docker-shell-streamlit

# Monitoring (Prometheus + Grafana)
make monitoring-up
make monitoring-down
```

## 📈 Monitoring stack (optional)

Start the application first, then attach the monitoring overlay:

```bash
make docker-up          # or make docker-up-build
make monitoring-up
```

| Service    | URL | Notes |
|------------|-----|-------|
| Prometheus | http://localhost:9090 | Scrapes `api:8000/metrics` every 15s |
| Grafana    | http://localhost:3000 | Default login: `admin` / `admin` |
| API metrics| http://localhost:8000/metrics | Prometheus text format |

**Exposed metrics** (see `src/metrics.py`):

- `rag_retrieval_latency_seconds` — histogram of Qdrant retrieval time
- `rag_documents_retrieved_total{collection}` — documents retrieved per collection
- `dicom_uploads_total` — DICOM uploads via `/analyze-case` and `/upload-doc`
- Standard HTTP metrics from `prometheus-fastapi-instrumentator` (latency, status codes)

Grafana loads the **RAG Metrics** dashboard from `monitoring/grafana/dashboards/rag-metrics.json` (datasource provisioned in `monitoring/grafana/provisioning/`).

```bash
make monitoring-down    # stops Prometheus/Grafana only
```

## 🔧 Development mode

For development with hot reload:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This mounts source volumes in read-only mode and enables automatic reload.

## 📦 Docker images

Images use **multi-stage builds** to optimize size:

- **Builder stage**: installs dependencies with compilers
- **Final stage**: Python slim runtime + application only
- **API image**: runs as non-root user `appuser` (see `Dockerfile.api`)

### Image tags

```bash
# Local build
rag-healthcare-api:latest
rag-healthcare-streamlit:latest

# GitHub Container Registry (when pushed)
ghcr.io/<username>/rag-healthcare-api:latest
ghcr.io/<username>/rag-healthcare-streamlit:latest
```

## 🔐 GitHub Container Registry

Images are automatically built and pushed to GitHub Container Registry (GHCR) when:

- Push to branch `main`
- Creation of tag `v*.*.*`

To use images from GHCR:

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull
docker pull ghcr.io/<username>/rag-healthcare-api:latest
docker pull ghcr.io/<username>/rag-healthcare-streamlit:latest

# Run
docker-compose up -d
```

## 📊 Health checks

Each container has a configured health check:

- **Qdrant**: `curl http://localhost:6333/health`
- **API**: `python -c "import requests; requests.get('http://localhost:8000/list-docs?rag_type=cases')"`
- **Streamlit**: `curl http://localhost:8501/_stcore/health`

Check status:

```bash
docker-compose ps
make docker-ps
```

## 🔍 Troubleshooting

### Container does not start

```bash
# Check logs
docker-compose logs api

# Verify network
docker network ls
docker network inspect rag-system-4-healthcare_rag-network
```

### Qdrant does not connect

```bash
# Verify health
curl http://localhost:6333/health

# Recreate container
docker-compose up -d --force-recreate qdrant
```

### Hot reload does not work

```bash
# Use docker-compose.dev.yml
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Clean and restart from scratch

```bash
make docker-clean
make docker-up-build
```

## 🧪 Testing with Docker

```bash
# Build images for tests
docker-compose build

# Health test for all services
docker-compose up -d
sleep 30
curl http://localhost:8000/list-docs?rag_type=cases
curl http://localhost:8501/_stcore/health

# Stop
docker-compose down -v
```

## 🔒 Security scanning & CI

The `docker-build.yml` workflow runs on every push/PR to `main` and on version tags:

1. **Hadolint** — lints `Dockerfile.api` and `Dockerfile.streamlit` before build
2. **Build** — multi-stage images with GHA cache; PRs load images locally for integration tests
3. **Trivy** — scans built images; **fails the job** on `HIGH` or `CRITICAL` vulnerabilities (`ignore-unfixed: true`)
4. **On `main` push** — images pushed to GHCR + SARIF uploaded to GitHub Security tab

Related workflows:

- `ci.yml` — unit tests (Python 3.10, 3.11, 3.12); ruff, black, and isort are **blocking**
- `security-scan.yml` — pip-audit, Gitleaks, Bandit
- `release.yml` — on tag `v*.*.*`, generates changelog with [git-cliff](https://git-cliff.org/) and creates a GitHub Release

## 📐 Volumes and persistence

```yaml
volumes:
  qdrant_storage:  # Persistent Qdrant data

  # Local mounts (development)
  ./data:/app/data  # DICOM dataset
```

### Qdrant backup

```bash
# Backup
docker run --rm -v rag-system-4-healthcare_qdrant_storage:/data   -v $(pwd)/backups:/backup alpine tar czf /backup/qdrant-backup.tar.gz /data

# Restore
docker run --rm -v rag-system-4-healthcare_qdrant_storage:/data   -v $(pwd)/backups:/backup alpine tar xzf /backup/qdrant-backup.tar.gz -C /
```

## 🌐 Production deployment

For production deployment:

1. Edit `docker-compose.yml`:
   - Remove development volumes
   - Configure `restart: always`
   - Use secrets for API keys
   - Enable HTTPS with a reverse proxy

2. Use environment variables:
   ```bash
   ENVIRONMENT=production docker-compose up -d
   ```

3. Configure reverse proxy (nginx/traefik):
   ```nginx
   location /api {
       proxy_pass http://localhost:8000;
   }
   location / {
       proxy_pass http://localhost:8501;
   }
   ```

## 📚 Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
