FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY apps/frontend/package*.json ./
RUN npm ci
COPY apps/frontend/ ./
RUN npm run build

# Caddy 2.11.9 is the version the assistant route was tested on (handle_errors needs 2.8+).
# The index digest's linux/amd64 layers equal the Caddy layers of the 149c11e release image.
FROM caddy:2.11.9-alpine@sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist/ /srv/
