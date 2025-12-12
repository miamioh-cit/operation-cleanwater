FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 iputils-ping && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh
EXPOSE 1502 1102 8080
ENTRYPOINT ["/app/entrypoint.sh"]
