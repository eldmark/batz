# Evaluador semántico MM3032: solo librería estándar, sin dependencias que instalar.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home logos
WORKDIR /app
COPY evaluador.py ./
COPY src ./src
USER logos

EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/')"
# Dentro del contenedor hay que escuchar en 0.0.0.0; compose solo lo publica en localhost.
CMD ["python", "evaluador.py", "--host", "0.0.0.0", "--port", "8765", "--no-browser"]
