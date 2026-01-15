# ARES - Things To Address

Last updated: 2026-01-13

## High Priority

### Security
- [x] **Hardcoded dev API key** - Fixed. Now uses `get_internal_api_key()` from `api/utils.py` which raises `ConfigurationError` in production if not set.
- [ ] **Bare exception catches** - Several places catch `Exception` broadly which can hide bugs. Consider catching specific exceptions in:
  - `api/auth.py` (lines 246-255)
  - `api/chat_views.py`
  - `api/calendar_views.py`
- [ ] **localStorage for tokens** - Frontend stores Auth0 tokens in localStorage which is vulnerable to XSS. Consider using `auth0-react`'s built-in memory storage or httpOnly cookies.

### Backend
- [ ] **N+1 query potential** - Review database queries in views that iterate over related objects. Consider using `select_related()` or `prefetch_related()`.
- [ ] **Missing database indexes** - Review frequently queried fields and add indexes where needed.
- [ ] **Log rotation** - Gunicorn and Vite logs will grow indefinitely. Set up logrotate:
  ```bash
  # /etc/logrotate.d/ares
  /home/gabe/ares/logs/*.log {
      daily
      rotate 7
      compress
      missingok
      notifempty
  }
  ```

### Frontend
- [ ] **Error boundaries** - Add React error boundaries to prevent full app crashes from component errors.
- [ ] **Loading states** - Some API calls lack proper loading indicators.
- [ ] **Offline handling** - No graceful handling when API is unreachable.

---

## Medium Priority

### Code Quality
- [ ] **Type hints** - Python code lacks type hints in many places. Consider adding for better IDE support and catching bugs.
- [ ] **API documentation** - No OpenAPI/Swagger docs for the API endpoints. Consider adding `drf-spectacular`.
- [ ] **Frontend TypeScript** - Consider migrating from JSX to TSX for type safety.
- [ ] **Test coverage** - Archived test files exist but unclear if they pass or are comprehensive. Set up pytest with coverage reporting.

### Infrastructure
- [ ] **Health check endpoint** - Add `/api/v1/health/` endpoint for monitoring that checks:
  - Database connectivity
  - Redis/cache connectivity
  - External service availability (Auth0, OpenRouter)
- [ ] **Monitoring** - No application monitoring. Consider:
  - Sentry for error tracking
  - Prometheus + Grafana for metrics
  - Uptime monitoring (UptimeRobot, etc.)
- [ ] **Backup strategy** - PostgreSQL database needs automated backups:
  ```bash
  # Example cron job
  0 2 * * * pg_dump -U ares ares | gzip > /backups/ares-$(date +\%Y\%m\%d).sql.gz
  ```
- [ ] **SSL certificate renewal** - Verify certbot auto-renewal is working:
  ```bash
  sudo certbot renew --dry-run
  ```

### Performance
- [ ] **Static asset caching** - Add cache headers for static files in nginx.
- [ ] **Database connection pooling** - `CONN_MAX_AGE` is set to 60s but consider using PgBouncer for better pooling.
- [ ] **CDN for static assets** - Consider CloudFlare or similar for caching static files globally.

---

## Low Priority / Nice to Have

### Features
- [ ] **API versioning** - Currently using `/api/v1/` but no actual versioning strategy.
- [ ] **Rate limit feedback** - When rate limited, return `Retry-After` header to clients.
- [ ] **Audit logging** - Log security-relevant actions (logins, permission changes, etc.).
- [ ] **Session management** - Allow users to view/revoke active sessions.

### Developer Experience
- [ ] **Pre-commit hooks** - Set up pre-commit for linting, formatting:
  ```yaml
  # .pre-commit-config.yaml
  repos:
    - repo: https://github.com/psf/black
      hooks:
        - id: black
    - repo: https://github.com/pycqa/flake8
      hooks:
        - id: flake8
  ```
- [ ] **CI/CD pipeline** - No automated testing/deployment. Consider GitHub Actions.
- [ ] **Development documentation** - Document local setup, architecture decisions.

### Cleanup
- [ ] **Unused dependencies** - Audit `requirements.txt` and `package.json` for unused packages.
- [ ] **Dead code** - Search for unused functions/imports.
- [ ] **Console.log statements** - Check frontend for debug console.log statements.

---

## Completed Recently

- [x] JWKS fetch timeout added (10s)
- [x] Rate limiting on auth endpoints
- [x] Thread-safe caching for Management API token and role cache
- [x] Removed print statements from production code
- [x] Frontend hot reload setup with systemd service
- [x] Service manager script (`manage-services.sh`)
- [x] Nginx configs for dev/prod modes
- [x] PostgreSQL migration from SQLite
- [x] SSL/HTTPS with Let's Encrypt
- [x] Systemd services for backend and frontend

---

## Notes

### Environment Variables to Review
Check `.env` has proper production values for:
- `DEBUG=False`
- `SECRET_KEY` - unique, random value
- `INTERNAL_API_KEY` - not the default
- `ALLOWED_HOSTS` - only production domains

### Quick Commands
```bash
# Service management
./manage-services.sh

# Switch frontend modes
./scripts/switch-frontend-mode.sh dev|prod|status

# View logs
tail -f logs/gunicorn-error.log
tail -f logs/vite-dev.log

# Database backup
pg_dump -U ares ares > backup.sql
```
