FROM python:3.11-slim

# Instalar Tesseract OCR + idioma español + poppler para PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear directorio temporal para OCR
RUN mkdir -p /tmp

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]