# Ultra-lightweight Python 3.10 Alpine container for 24/7 cloud execution
FROM python:3.10-alpine

# Set environment flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Copy application code
COPY app.py .

# Healthcheck for Railway / Docker
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + str(os.environ.get('PORT', 8080)) + '/health', timeout=3)" || exit 1

EXPOSE 8080

# Run standalone threaded server (0 external pip dependencies required)
CMD ["python", "app.py"]
