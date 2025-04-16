# Use Python 3.13 as the base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv

# Copy pyproject.toml
COPY pyproject.toml .

# Create a virtual environment
RUN uv venv create

# Create a virtual environment
RUN uv sync

# Install dependencies using UV with pyproject.toml
RUN uv pip install --no-cache .

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]