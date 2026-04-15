FROM mcr.microsoft.com/playwright/python:v1.51.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
COPY sql ./sql

RUN pip install --no-cache-dir .

CMD ["python", "-m", "app.run_once"]
