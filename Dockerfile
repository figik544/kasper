__pycache__
*.pyc
*.pyo
*.pyd
env/
.git
.vscode/
*.md
*.log
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for PyNaCl
# These dependencies are necessary for building and running packages
# like PyNaCl that require compilation of C extensions.
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]