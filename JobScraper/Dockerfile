# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project configuration
COPY pyproject.toml uv.lock ./

# Install project dependencies
# --frozen ensures we stick to the lockfile
RUN uv sync --frozen --no-install-project

# Install Playwright browsers and system dependencies
# We verify the path to ensure we use the installed playwright
ENV PATH="/app/.venv/bin:$PATH"

# Install Chromium and its system dependencies
# --with-deps installs system packages via apt-get
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

# Install the project itself
RUN uv sync --frozen

# Expose port
EXPOSE 3000

# Start command
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
