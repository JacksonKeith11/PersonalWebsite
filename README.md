# Personal site

Resume site plus (eventually) an aggregator for web serial updates. Python/FastAPI, run in Docker via OrbStack, exposed via Cloudflare Tunnel.

## Layout

- `app/main.py` — FastAPI app (`/` resume, `/healthz`, `/api/serials` placeholder)
- `app/static/` — resume HTML/CSS
- `data/` — persistent runtime data (gitignored)
- `.env` — secrets (gitignored); see `.env.example`

## Run locally

```sh
docker compose up -d --build
open http://localhost:8080
```

## Expose on your domain

1. Cloudflare dashboard → Zero Trust → Networks → Tunnels → create a tunnel (Docker connector).
2. Put the token in `.env` as `CLOUDFLARE_TUNNEL_TOKEN`.
3. Add a public hostname for your domain pointing to `http://web:8000`.
4. `docker compose --profile tunnel up -d`
