
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY server.py relay_client.py relay_session.py ./
COPY remote_server.py user_session.py tools.py workflow_builder.py ./

COPY oauth/ ./oauth/

RUN useradd --create-home --uid 10001 mcpuser

USER mcpuser

EXPOSE 8001

CMD ["python", "remote_server.py"]
