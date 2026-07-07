# Build context is the repository root (so the sibling `chromadose/` package is
# available to the editable dependency in pyproject.toml).
#   docker build -f web/backend/Dockerfile -t chromadose-web .
FROM python:3.12-slim

# System libs matplotlib/scipy wheels may need at runtime are already in the
# manylinux wheels; keep the image lean.
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the library and the backend, preserving the relative layout the backend's
# pyproject expects (../../chromadose).
COPY chromadose /app/chromadose
COPY web/backend /app/web/backend

WORKDIR /app/web/backend
RUN pip install .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
