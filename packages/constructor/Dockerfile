FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy package files
COPY pyproject.toml README.md ./
COPY src ./src

# Install the package
RUN uv pip install --system --no-cache .

# Run scp-cli by default
ENTRYPOINT ["scp-cli"]
CMD ["--help"]
