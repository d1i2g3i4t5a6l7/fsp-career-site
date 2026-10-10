FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# gid 10001 — по нему runner пускает к своему сокету только workspace
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY certs ./certs
COPY tasks ./tasks
COPY app ./app

USER app
EXPOSE 8010
# Один процесс: шина WebSocket, очереди к моделям и фоновые проверки живут в памяти
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
