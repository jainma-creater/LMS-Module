# Course video renderer (Remotion + headless Chromium). Internal service only.
FROM node:24-bookworm-slim

# Libraries required by Remotion's headless Chromium.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates fonts-liberation fonts-dejavu-core \
        libnss3 libatk-bridge2.0-0 libatk1.0-0 libxkbcommon0 libgbm1 libasound2 \
        libxcomposite1 libxdamage1 libxrandr2 libpango-1.0-0 libcairo2 libcups2 \
        libdrm2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production \
    PORT=8080 \
    OUTPUT_DIR=/data/videos \
    NARRATION_DIR=/tmp/narration

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig.json server.mjs ./
COPY src ./src

RUN mkdir -p /data/videos /tmp/narration
EXPOSE 8080
CMD ["node", "server.mjs"]
