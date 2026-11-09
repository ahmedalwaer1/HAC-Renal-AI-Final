FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-api.txt ./

RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

RUN mkdir -p /app/data /app/tools && \
    cp /app/clinical_data.py /app/data/clinical_data.py && \
    cp /app/clinical_vocabulary.py /app/data/clinical_vocabulary.py && \
    cp /app/drug_bounds.py /app/data/drug_bounds.py && \
    cp /app/drug_registry.py /app/data/drug_registry.py && \
    cp /app/crcl_calculator.py /app/tools/crcl_calculator.py && \
    touch /app/data/__init__.py /app/tools/__init__.py

CMD ["sh", "-c", "exec python -m uvicorn api_bridge:app --host 0.0.0.0 --port ${PORT:-8000}"]
