FROM python:3.12-slim

WORKDIR /app
COPY ipod_backup.py /app/ipod_backup.py
COPY LICENSE /app/LICENSE

ENTRYPOINT ["python", "/app/ipod_backup.py"]
