# Docker Setup Guide

This project is fully containerized with Docker to ensure isolation and reproducibility.

## 🏗️ Architecture

The system is composed of 3 separate containers:

1. **qdrant** - Vector database (official image)
2. **api** - FastAPI backend (port 8000)
3. **streamlit** - Streamlit frontend (port 8501)

All containers communicate through the private Docker network `rag-network`.

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

## 🔒 Security scanning

CI/CD pipelines include:

- **Trivy**: container vulnerability scanning
- **Docker Bench**: best-practice checks
- **SARIF Upload**: results in GitHub Security

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
