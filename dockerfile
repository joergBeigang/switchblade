FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# -----------------------------
# System dependencies (PySide6 / Qt / Nuitka)
# -----------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    patchelf \
    git \
    python3-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    libglib2.0-0 \
    libgl1 \
    libxkbcommon-x11-0 \
    libegl1 \
    libfontconfig1 \
    libdbus-1-3 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libsm6 \
    libice6 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Workdir
# -----------------------------
WORKDIR /app

# -----------------------------
# Python tooling
# -----------------------------
RUN pip install --upgrade pip setuptools wheel nuitka

# -----------------------------
# Python dependencies (your project)
# -----------------------------
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# -----------------------------
# Default shell (dev mode)
# -----------------------------
CMD ["/bin/bash"]
