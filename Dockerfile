# Evaluador semántico MM3032: solo librería estándar de Python; el único paquete del sistema es espeak-ng
# (voz de la explicación guiada: genera el audio dentro del contenedor, sin enviar texto a ningún servicio).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8765
RUN apt-get update \
 && apt-get install -y --no-install-recommends espeak-ng \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home logos
WORKDIR /app
COPY evaluador.py ./
COPY src ./src
# aquí se guardan las palabras que la persona añade al diccionario (se monta como volumen)
RUN mkdir -p /app/datos && chown logos /app/datos
USER logos

EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT', '8765'))"
# Dentro del contenedor hay que escuchar en 0.0.0.0; compose solo lo publica en localhost.
# El puerto sale de la variable PORT (8765 por defecto; los alojamientos la reemplazan).
CMD ["python", "evaluador.py", "--host", "0.0.0.0", "--no-browser"]
