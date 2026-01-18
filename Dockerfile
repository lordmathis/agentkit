# Stage 1: Build Web UI
FROM node:24-slim AS webui-builder

WORKDIR /app/webui

COPY webui/package.json webui/package-lock.json* ./
RUN npm install

COPY webui/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY agentkit/ ./agentkit/
COPY --from=webui-builder /app/webui/dist ./webui/dist

EXPOSE 8000
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uv", "run", "python", "-m", "agentkit.main"]
