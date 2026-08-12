# Docker

Images live here. The compose file is at the **repository root**:

```bash
# from the repo root
docker compose up --build
```

- `Dockerfile` — Django 5.2 / Python 3.12 backend
- `Dockerfile.frontend-next` — Next.js 15 / Node 22 frontend
- `nginx.conf` — reverse proxy (HTTP for local; terminate TLS at a load balancer in production)
