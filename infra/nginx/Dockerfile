FROM owasp/modsecurity-crs:nginx-alpine

USER root
RUN rm -f /docker-entrypoint.d/01-check-low-port.sh

ENV PORT=80
ENV SSL_PORT=443
ENV SERVER_NAME=localhost
ENV MODSEC_RULE_ENGINE=on

# Copy exclusions into CRS rules directory
COPY modsecurity/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf /etc/modsecurity.d/owasp-crs/rules/

# Copy default server block template
COPY conf.d/default.conf /etc/nginx/templates/conf.d/default.conf.template

EXPOSE 80 443
