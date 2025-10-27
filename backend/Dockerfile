# Use slim Python image
FROM python:3.11-slim

WORKDIR /app

# Install runtime deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Copy backend source
COPY app ./app

# Environment defaults (can be overridden)
ENV SIM_MODE=SIM \
    TELEMETRY_RATE=5 \
    PORT=5000 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

# Run the server
CMD ["python", "-m", "app.server"]
