# Use Python 3.12 slim image for a lightweight backend
FROM python:3.12-slim as backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Use Node.js for frontend build
FROM node:20-slim as frontend-builder

WORKDIR /app

# Copy frontend config and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Final production image
FROM python:3.12-slim

WORKDIR /app

# Copy backend and installed packages from builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /app/backend ./backend

# Copy built frontend assets
COPY --from=frontend-builder /app/dist ./frontend/dist

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_MODE=production

# Expose port (FastAPI/RPC port)
EXPOSE 8000

# Entry point (Simulated for this production-ready setup)
CMD ["python", "backend/main.py"]
