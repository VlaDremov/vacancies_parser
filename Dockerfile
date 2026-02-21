FROM mcr.microsoft.com/playwright/python:v1.51.0-jammy

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir .

CMD ["python", "-m", "app.run_once"]
