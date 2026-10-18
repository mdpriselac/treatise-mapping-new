# Static site: build with Astro + Pagefind, serve with nginx on Cloud Run.
FROM node:22-slim AS build
WORKDIR /site
COPY site/package.json site/package-lock.json ./
RUN npm ci
COPY site/ ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/security-headers.conf /etc/nginx/conf.d/security-headers.inc
COPY --from=build /site/dist /usr/share/nginx/html
EXPOSE 8080
