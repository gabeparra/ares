# ARES Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed and running (for local LLM)

## Backend Setup (Django)

1. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```bash
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
OLLAMA_BASE_URL=http://localhost:11434
AUTH0_DOMAIN=your-auth0-domain
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_AUDIENCE=your-auth0-audience
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

6. Start the Django development server:
```bash
python manage.py runserver
```

The backend will be available at `http://127.0.0.1:8000`

## Frontend Setup (React + Vite)

1. Install Node.js dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

The Vite dev server is configured to proxy API requests to the Django backend.

## Development Workflow

1. Start Ollama (if not already running):
```bash
ollama serve
```

2. In one terminal, start Django:
```bash
source .venv/bin/activate
python manage.py runserver
```

3. In another terminal, start the frontend:
```bash
npm run dev
```

4. Open `http://localhost:3000` in your browser

## API Endpoints

- `POST /api/v1/chat` - Send a chat message
- `GET /api/v1/models` - List available models
- `POST /api/v1/models` - Set current model
- `GET /api/v1/sessions` - List conversation sessions
- `GET /api/v1/conversations?session_id=<id>` - Get conversations for a session

## Next Steps

- Implement Auth0 authentication
- Add database models for sessions and conversations
- Add WebSocket support for real-time updates
- Implement Telegram bot integration

