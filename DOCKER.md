# Docker Setup for ARES

This guide explains how to run ARES using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- Ollama installed and running on the host machine (if using LLM features)

## Quick Start

1. Copy `.env.example` to `.env` and configure (optional, defaults are provided):
```bash
cp .env.example .env
```

Edit `.env` and set your values:
```bash
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
OLLAMA_BASE_URL=http://host.docker.internal:11434
AUTH0_DOMAIN=your-auth0-domain
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_AUDIENCE=your-auth0-audience
```

2. Ensure Ollama is running on your host machine (if using LLM features):
```bash
ollama serve
```

3. Build and start all services:
```bash
docker-compose up --build
```

This will start:
- **Backend** (Django) on `http://localhost:8000`
- **Frontend** (React) on `http://localhost` (port 80)

**Note:** Ollama must be running separately on your host machine. The backend will connect to it via `host.docker.internal:11434`.

## Services

### Backend (Django)
- Port: 8000
- Automatically runs migrations on startup
- Database: SQLite (persisted in `db.sqlite3`)

### Frontend (React)
- Port: 80 (default HTTP port - accessible without specifying port)
- Serves built React app via Nginx
- Proxies API requests to backend

### Ollama (Host Machine)
- Must be running on the host machine
- Default port: 11434
- The backend connects via `host.docker.internal:11434`
- Pull models with: `ollama pull llama3.2:3b` (run on host machine)

## Development Mode

For development with hot-reload, use the development override:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This will:
- Mount source code as volumes for hot-reload
- Run Vite dev server instead of production build
- Enable Django auto-reload

### Or run services separately:

**Backend only:**
```bash
docker-compose up backend
# Or run locally:
source .venv/bin/activate
python manage.py runserver
```

**Frontend only:**
```bash
npm install
npm run dev
```

**Ollama:**
Ollama runs on the host machine, not in Docker. Start it with:
```bash
ollama serve
```

## Useful Commands

### View logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Stop all services:
```bash
docker-compose down
```

### Stop and remove volumes:
```bash
docker-compose down -v
```

### Rebuild a specific service:
```bash
docker-compose build backend
docker-compose up -d backend
```

### Access Django shell:
```bash
docker exec -it ares-backend python manage.py shell
```

### Create Django superuser:
```bash
docker exec -it ares-backend python manage.py createsuperuser
```

### Pull Ollama models (on host machine):
```bash
ollama pull llama3.2:3b
ollama pull mistral-nemo:12b
```

## Production Considerations

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Use a proper `DJANGO_SECRET_KEY`
3. Replace SQLite with PostgreSQL:
   - Add PostgreSQL service to `docker-compose.yml`
   - Update `DATABASES` in `settings.py`
4. Configure proper `ALLOWED_HOSTS`
5. Set up SSL/TLS certificates
6. Use environment-specific settings

## Troubleshooting

### Backend won't start:
- Check logs: `docker-compose logs backend`
- Ensure migrations run: `docker exec ares-backend python manage.py migrate`

### Frontend shows connection errors:
- Verify backend is running: `docker-compose ps`
- Check CORS settings in Django settings

### Backend can't connect to Ollama:
- Ensure Ollama is running on host: `ollama serve`
- Check `OLLAMA_BASE_URL` in `.env` (should be `http://host.docker.internal:11434` for Docker)
- On Linux, you may need to use `host.docker.internal` or configure Docker networking
- For local development (non-Docker), use `http://localhost:11434`

