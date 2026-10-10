FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Пакеты, доступные коду кандидата сверх стандартной библиотеки
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY server.py /opt/runner/server.py

# Сервер под root только чтобы запускать код кандидата под отдельными uid; сам код root не получает
CMD ["python", "/opt/runner/server.py"]
