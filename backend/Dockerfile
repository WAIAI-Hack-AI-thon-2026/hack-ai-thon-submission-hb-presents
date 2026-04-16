FROM python:3.11-slim

WORKDIR /app

# dependencies
COPY requirements-local.txt .
RUN pip install --no-cache-dir -r requirements-local.txt

# copy source code
COPY . .

# run FastAPI on port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]