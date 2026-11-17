# Builds the React app and serves it with Caddy, which also proxies the API (see deploy/Caddyfile)
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Empty = call the API on the same origin (Caddy routes /api to the backend)
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM caddy:2.8-alpine
COPY --from=build /app/dist /srv
