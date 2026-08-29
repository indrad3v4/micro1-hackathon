# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

COPY creative-court/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime deps
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy source code
COPY creative-court/src /app/src
COPY creative-court/app /app/app
COPY creative-court/demo_briefs /app/demo_briefs

# Create traces directory
RUN mkdir -p /app/traces

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
