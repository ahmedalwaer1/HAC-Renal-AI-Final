FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-api.txt ./

RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

CMD ["sh", "-c", "exec python -m uvicorn api_bridge:app --host 0.0.0.0 --port ${PORT:-8000}"]
