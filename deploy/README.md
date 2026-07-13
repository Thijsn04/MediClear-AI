# Deployment

Production deployment artifacts for MediClear AI. Pick the path that matches
your environment.

| Path | Use when | Files |
|------|----------|-------|
| Docker Compose (simple) | single node, quick start | `docker-compose.yml` |
| Docker Compose (production) | single node with Redis, limits | `docker-compose.prod.yml` |
| Kubernetes / Helm | a cluster, autoscaling, HA | `deploy/helm/mediclear/` |
| Nginx reverse proxy | TLS termination in front of any of the above | `deploy/nginx/mediclear.conf` |

Before deploying, read [docs/configuration.md](../docs/configuration.md) and set,
at minimum: `AI_PROVIDER`, the matching key/model, `REQUIRE_API_KEY=true` with
`API_KEYS`, and `ALLOWED_ORIGINS`.

---

## 1. Docker Compose (production, with Redis)

```bash
cp .env.example .env          # set AI_PROVIDER + key/model + API_KEYS
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f mediclear
```

This starts the app plus Redis (durable sessions, cache, rate limiting) with
`REDIS_URL` wired automatically, resource limits, and health checks. Put Nginx
(below) in front for TLS.

---

## 2. Kubernetes with Helm

The chart lives in `deploy/helm/mediclear`. It ships a Deployment, Service,
Ingress, HPA, ConfigMap, Secret, and an optional in-cluster Redis.

```bash
# 1. Create the API-key/provider secret out-of-band (recommended):
kubectl create secret generic mediclear-secrets \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=API_KEYS=team-a-key,team-b-key

# 2. Install, referencing that secret and your host:
helm install mediclear ./deploy/helm/mediclear \
  --set existingSecret=mediclear-secrets \
  --set config.AI_PROVIDER=openai \
  --set config.OPENAI_MODEL=gpt-4o \
  --set ingress.hosts[0].host=mediclear.example.com \
  --set ingress.tls[0].hosts[0]=mediclear.example.com \
  --set ingress.tls[0].secretName=mediclear-tls
```

Key `values.yaml` knobs: `replicaCount`, `autoscaling.*`, `resources.*`,
`ingress.*`, `redis.enabled`, and the `config` map (non-secret env vars). The
ingress annotations already disable proxy buffering so SSE chat streams live.

Upgrade / uninstall:

```bash
helm upgrade mediclear ./deploy/helm/mediclear -f my-values.yaml
helm uninstall mediclear
```

> Do not commit real API keys into `values.yaml`. Use `existingSecret` (shown
> above) or a sealed-secrets / external-secrets operator.

---

## 3. Nginx reverse proxy (TLS)

`deploy/nginx/mediclear.conf` terminates TLS, adds security headers (HSTS,
CSP, nosniff, frame-deny), enforces the upload ceiling, streams SSE without
buffering, and firewalls `/metrics` to a private network.

```bash
# Put your cert/key at /etc/nginx/tls/{fullchain,privkey}.pem
cp deploy/nginx/mediclear.conf /etc/nginx/conf.d/mediclear.conf
# edit server_name and upstream to match your setup
nginx -t && systemctl reload nginx
```

The bundled frontend is fully self-contained, so the strict `Content-Security-Policy`
in the config works without exceptions.

---

## Production checklist

- [ ] `REQUIRE_API_KEY=true` and real `API_KEYS` set (kept out of source).
- [ ] `ALLOWED_ORIGINS` restricted to your frontend origin(s).
- [ ] TLS terminated by Nginx / ingress; HSTS on.
- [ ] `REDIS_URL` set (compose-prod and Helm do this for you) for multi-instance.
- [ ] Rate limits (`RATE_LIMIT_*`) tuned to your provider budget.
- [ ] For PHI: consider `ZERO_RETENTION=true` and a local `AI_PROVIDER` (Ollama).
- [ ] `/metrics` scraped privately, not exposed publicly.
- [ ] Health probes green: `GET /api/v1/health`.
