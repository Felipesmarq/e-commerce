FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache build-base libffi-dev

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para rodar o servidor FastAPI na porta 5001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]