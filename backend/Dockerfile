# ── Stage 1: TeX Live base ────────────────────────────────────────────────────
# We use the official TeX Live image so pdflatex is already available.
# Then we install Python on top of it.
FROM ubuntu:22.04

# Prevents interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install Python, pip, and a lean but complete TeX Live distribution
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Confirm pdflatex is available
RUN pdflatex --version

# ── Stage 2: Python app ───────────────────────────────────────────────────────
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port Render / cloud platform will map to
EXPOSE 8000

# Use shell form (not exec form) so $PORT env var is expanded at runtime.
# Render sets PORT=10000; locally it defaults to 8000.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
