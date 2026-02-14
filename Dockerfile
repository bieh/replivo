FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY cli/ cli/
COPY tests/ tests/
COPY samples/ samples/
COPY --from=frontend /app/frontend/dist frontend/dist

RUN chmod +x /app/backend/start.sh
WORKDIR /app/backend
CMD ["/app/backend/start.sh"]
