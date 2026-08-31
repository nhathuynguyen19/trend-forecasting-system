FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
WORKDIR /app
RUN pip install --no-cache-dir playwright==1.48.0 \
    && playwright install chromium --with-deps
COPY main.py .
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
