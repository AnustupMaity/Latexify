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
    pandoc \
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
EXPOSE 10000

# Default port to 10000 (Render's default). Override locally with -e PORT=8000.
ENV PORT=10000

# Exec form with shell expansion via sh -c so $PORT is resolved at runtime
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
