---
paths:
  - "**/docker-compose*.{yml,yaml}"
  - "**/compose*.{yml,yaml}"
  - "**/Dockerfile*"
  - "**/.dockerignore"
---

# Docker Compose Conventions

## v2 spec, no version key

Compose v2 — do NOT include a top-level `version:` field. It is obsolete and emits a warning. Follow the existing compose files in this repo as the reference.

## Healthchecks are mandatory

Every service MUST define a `healthcheck:`. Without one, zero-downtime swap tooling cannot operate and dependent services with `depends_on: condition: service_healthy` will hang forever.

<!-- For services exposed only via a reverse proxy (no host port mapping), localhost-based
     healthchecks won't work from outside the container. Two acceptable patterns:
       1. Run the check inside the container via `docker exec` (curl localhost:PORT
          from within the service network).
       2. Have the service ship its own /health endpoint and check it internally. -->

## Environment substitution

Use `${VAR}` substitution from `.env` for image tags, registry URLs, domains, ports, secrets. Never hardcode:

- `image: ${REGISTRY}/myapp:${TAG}` — yes
- `image: registry.example.com/myapp:latest` — no

The `.env` file lives next to the compose file. Never commit real `.env` files; commit `.env.example` instead.

## Networks

Don't pre-create networks with `docker network create` before `compose up`. Let Compose own them — name them in the file and they'll be created/torn down with the stack. External networks are the rare exception (cross-stack proxy attachment).

## Reverse-proxy routing

All HTTP routing is declared via labels on the service (or via the proxy's file/dynamic provider for non-Docker workloads). Do not edit Nginx, Apache, or other reverse-proxy config files manually unless that proxy is the project's chosen tool.

## Dockerfiles

- Pin base images to a specific version tag (or digest). Never use `:latest`.
- Use multi-stage builds. The runtime stage copies only built artifacts.
- Run as a non-root `USER` in the final stage.
- Order layers for cache reuse: dependency manifests first, then source.
- Keep secrets out of `ARG`/`ENV`/layers. Use BuildKit `--secret` mounts.
- Keep `.dockerignore` current (`.git`, `node_modules`, `.env*`, build output).
- Add a `HEALTHCHECK`, or define it in compose.
