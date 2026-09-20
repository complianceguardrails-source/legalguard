# Guardrail generation service. Node plus a pinned opa binary -- opa is the
# reason this service exists (see lib/opa.js), so its version and checksum
# are fixed here rather than resolved at build time.
FROM node:22-slim

ARG OPA_VERSION=1.20.2
# sha256 of opa_linux_amd64_static for that release, verified against the
# published .sha256 file and an independent download when pinned. Bump both
# together.
ARG OPA_SHA256=69da5179ee403d10fa11bab6cfb4ffb0d23dba5f9b682fa977db772a1da5670f

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && curl -fsSL -o /usr/local/bin/opa \
      "https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/opa_linux_amd64_static" \
 && echo "${OPA_SHA256}  /usr/local/bin/opa" | sha256sum -c - \
 && chmod +x /usr/local/bin/opa \
 && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* \
 && opa version

WORKDIR /srv
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY server.js ./
COPY lib ./lib

ENV NODE_ENV=production
EXPOSE 8080
USER node
CMD ["node", "server.js"]
