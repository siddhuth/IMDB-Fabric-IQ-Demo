# Build from the REPO ROOT so the canonical agent prompt is in context:
#   docker build -t imdb-casting-graph -f webapp/Dockerfile .
FROM python:3.11-slim

WORKDIR /app
COPY webapp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webapp/ .
COPY config/agent_prompt.md ./agent_prompt.md

EXPOSE 8000
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
