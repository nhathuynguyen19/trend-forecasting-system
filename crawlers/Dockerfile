FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium --with-deps

COPY core/ ./core/
COPY platforms/ ./platforms/
COPY main.py .
COPY .env.example ./.env.example

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV BROWSER_HEADLESS=true

CMD ["python", "main.py"]