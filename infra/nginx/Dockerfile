FROM node:22-alpine AS frontend-builder

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM owasp/modsecurity-crs:4.25.2-nginx-alpine-202611190211-lts

USER root
RUN rm -f /docker-entrypoint.d/01-check-low-port.sh && \
    rm -rf /usr/share/nginx/html/*

ENV PORT=80
ENV SSL_PORT=443
ENV SERVER_NAME=localhost
ENV MODSEC_RULE_ENGINE=on
ENV BLOCKING_PARANOIA=2

# Copy compiled React SPA build
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

# Copy exclusions into CRS rules directory
COPY infra/nginx/modsecurity/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf /etc/modsecurity.d/owasp-crs/rules/

# Copy default server block template
COPY infra/nginx/conf.d/default.conf /etc/nginx/templates/conf.d/default.conf.template

EXPOSE 80 443
